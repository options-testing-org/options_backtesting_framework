import pytest
from options_test_helper import *

def test_test():
    assert True

@pytest.mark.xfail(raises=NameError)
def test_test_options_methods():
    put_4210 = get_4210_put_option()
    assert put_4210.price == 13.95
    update_4210_put_option(put_4210)
    assert put_4210.price == 8.95

    put_4220 = get_4220_put_option()  # 15.00
    assert put_4220.price == 15.00
    update_4220_put_option(put_4220)  # 9.65
    assert put_4220.price == 9.65

    put_4100 = get_4100_put_option()  # 6.75
    assert put_4100.price == 6.75
    update_4100_put_option(put_4100)  # 4.20
    assert put_4100.price == 4.20

    put_4075 = get_4075_put_option()  # 5.85
    assert put_4075.price == 5.85
    update_4075_put_option(put_4075)  # 3.60
    assert put_4075.price == 3.60

    call_4390 = get_4390_call_option()  # 4.20
    assert call_4390.price == 4.20
    update_4390_call_option(call_4390)  # 6.10
    assert call_4390.price == 6.10

    call_4380 = get_4380_call_option()  # 5.55
    assert call_4380.price == 5.55
    update_4380_call_option(call_4380)  # 8.10
    assert call_4380.price == 8.10

    call_4310 = get_4310_call_option()  # 30.85
    assert call_4310.price == 30.85
    update_4310_call_option(call_4310)  # 41.70
    assert call_4310.price == 41.70

    call_4320 = get_4320_call_option()  # 25.30
    assert call_4320.price == 25.30
    update_4320_call_option(call_4320)  # 34.70
    assert call_4320.price == 34.70
