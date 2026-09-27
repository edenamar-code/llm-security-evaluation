from enum import Enum


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class FindingStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
