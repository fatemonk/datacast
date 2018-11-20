import os
from datacast.base import cast, EnvironConfig


class Test(EnvironConfig):
    YEP: bool
    SPAM: int = 5
    HAM: str = '232'
    Q_TEST: bool = False


class Spam(Test):
    SPAM: round = 2
    HAM: float = 2.5
    T_TEST: bool = True


os.environ['SPAM'] = '10.9'
os.environ['YEP'] = 'off'
print(Spam()._asdict())
