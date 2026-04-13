import logging
import socket

import httpx

logger = logging.getLogger(__name__)


class DependencyCheckError(Exception):
    """Raised when dependency checks fail unexpectedly."""


class DependencyChecker:
    def __init__(
        self,
        dns_target: str = "quay.io",
        registry_urls: list[str] | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.dns_target = dns_target
        self.registry_urls = registry_urls or [
            "https://quay.io",
            "https://public.ecr.aws",
        ]
        self.timeout = timeout

    def check_dns(self) -> bool:
        try:
            socket.getaddrinfo(self.dns_target, 443)
            logger.info("DNS check passed for target=%s", self.dns_target)
            return True
        except socket.gaierror:
            logger.warning("DNS check failed for target=%s", self.dns_target)
            return False
        except Exception as exc:
            raise DependencyCheckError(f"Unexpected DNS check failure: {exc}") from exc

    def check_registry_reachability(self) -> bool:
        results: list[bool] = []

        for url in self.registry_urls:
            try:
                response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
                results.append(response.status_code < 500)
                logger.info(
                    "Registry reachability check url=%s status_code=%s",
                    url,
                    response.status_code,
                )
            except httpx.HTTPError:
                logger.warning("Registry reachability check failed for url=%s", url)
                results.append(False)
            except Exception as exc:
                raise DependencyCheckError(f"Unexpected registry check failure: {exc}") from exc

        return all(results) if results else False

    def collect_dependency_health(self) -> dict[str, bool]:
        dns_ok = self.check_dns()
        registry_ok = self.check_registry_reachability()

        result = {
            "dns_ok": dns_ok,
            "registry_ok": registry_ok,
        }

        logger.info(
            "Collected dependency health dns_ok=%s registry_ok=%s",
            dns_ok,
            registry_ok,
        )

        return result