from ...survey import BaseSrc
from .analytics import IDTtoxyz


class SourceField(BaseSrc):
    """Define the inducing field"""

    def __init__(self, receiver_list=None, parameters=[50000, 90, 0], **kwargs):
        assert (
            len(parameters) == 3
        ), "Inducing field 'parameters' must be a list or tuple of length 3 (amplitude, inclination, declination"

        self.parameters = parameters
        self.b0 = IDTtoxyz(-parameters[1], parameters[2], parameters[0])
        super(SourceField, self).__init__(
            receiver_list=receiver_list, parameters=parameters, **kwargs
        )
