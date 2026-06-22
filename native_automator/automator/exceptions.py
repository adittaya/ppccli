class DeviceError(Exception):
    pass

class ConnectionError(DeviceError):
    pass

class ElementNotFound(DeviceError):
    pass

class ActionFailed(DeviceError):
    pass
