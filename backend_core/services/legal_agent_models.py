import pydantic


class BaseResponse(pydantic.BaseModel):
    message: str
    code: int


class ComplianceResult(pydantic.BaseModel):
    original: str
    risk: str
    suggestion: str


class ComplianceResponseData(pydantic.BaseModel):
    compliance: bool
    result: list[ComplianceResult]


class ComplianceResponse(BaseResponse):
    data: ComplianceResponseData
