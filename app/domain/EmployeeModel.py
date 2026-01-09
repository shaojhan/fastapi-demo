from enum import Enum

class EmployeeEnum(str, Enum):
    """
    Docstring for EmployeeEnum
    
    HR: 人力資源部
    IT: 資訊科技部
    PR: 公關部
    RD: 研發部
    BD: 業務部
    """

    HR = 'HR'
    IT = 'IT'
    PR = 'PR'
    RD = 'RD'
    BD = 'BD'