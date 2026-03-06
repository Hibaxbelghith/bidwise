from rest_framework.throttling import AnonRateThrottle


class OTPRequestThrottle(AnonRateThrottle):
    """
    Limits OTP request attempts per IP address.
    10 requests per hour — prevents email bombing and enumeration.
    """
    rate = '10/hour'
