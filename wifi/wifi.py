from asyncio import sleep_ms, CancelledError
from logging import get_logger, Logger
from time import ticks_ms, ticks_diff

from network import WLAN, STA_IF  # todo micropython specific imports

try:
    from rp2 import country
except ImportError:
    def country(country_code: str):
        pass  # no-op for devices that don't support country


class Wifi:
    def __init__(self, ssid: str, password: str, country_code: str = 'US', power_mode=0xa11140, reset: bool = False):
        self._ssid = ssid
        self._password = password
        self.__country_code = None  # todo move to config
        self.__power_mode = None  # todo move to config
        self._log: Logger | None = None

        self.wlan: WLAN = WLAN(STA_IF)
        if reset:
            self.wlan.deinit()  # clear settings from last boot
        self.power_mode = power_mode
        self.country_code = country_code
        self._running = False

    def __str__(self):
        ip, subnet, gateway, dns = self.wlan.ifconfig()
        return f"Wifi(ssid='{self.ssid}', ip='{ip}', subnet='{subnet}', gateway='{gateway}', dns='{dns}')"

    def is_connected(self):
        return self.wlan.isconnected()

    def ip_address(self) -> str:
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]

    async def start(self, timeout: int = 10_000,
                    sleep_millis: int = 2000,
                    reconnect_callback=None,
                    failure_callback=None) -> None:
        try:
            await self.connect(timeout)
            await self.monitor(sleep_millis, reconnect_callback, failure_callback)
        except CancelledError:
            self.log.info("Wifi start coroutine cancelled")
        except Exception as error:
            self.log.error("Uncaught exception in wifi.start: {}", str(error))

    async def connect(self, timeout: int = 10_000) -> bool:
        self.wlan.active(True)
        return await self.reconnect(timeout)

    async def reconnect(self, timeout: int = 10_000) -> bool:
        start = ticks_ms()
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected() and self.wlan.status() >= 0 and ticks_diff(ticks_ms(), start) < timeout:
            await sleep_ms(50)
        if self.wlan.isconnected():
            self.log.info("{} Connected", self)
        else:
            self.log.warning("Unable to connect to wifi, reconnected timed out after {}ms",
                             ticks_diff(ticks_ms(), start))
        return self.wlan.isconnected()

    async def monitor(self, sleep_millis: int = 2000, reconnect_callback=None, failure_callback=None):
        self._running = True
        while self._running:
            try:
                self.log.trace("Checking wifi status, active = {}, connected = {}", self.wlan.active(),
                               self.wlan.isconnected())
                if self.wlan.active() and not self.wlan.isconnected():
                    if await self.reconnect():
                        if reconnect_callback is not None:
                            reconnect_callback(self.ip_address())
                    else:
                        if failure_callback is not None:
                            failure_callback()
            except CancelledError:
                self.log.info("Wifi monitor coroutine cancelled")
            except Exception as error:
                self.log.error("Uncaught exception: {}", str(error))
            finally:
                await sleep_ms(sleep_millis)

    @property
    def ssid(self) -> str:
        return self._ssid

    @property
    def password(self) -> str:
        return self._password

    @property
    def country_code(self) -> str:
        return self.__country_code

    @country_code.setter
    def country_code(self, country_code: str = 'US') -> None:
        if self.__country_code != country_code:
            self.__country_code = country_code
            country(country_code)

    @property
    def power_mode(self) -> int:
        return self.__power_mode

    @power_mode.setter
    def power_mode(self, power_mode: int) -> None:
        if self.__power_mode != power_mode:
            self.__power_mode = power_mode
            self.wlan.config(pm=power_mode)  # Disable power-save mode

    @property
    def log(self) -> Logger:
        if self._log is None:
            self._log = get_logger(__name__)
        return self._log
