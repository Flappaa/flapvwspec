from vlinker.vw_helpers import (
    longcoding_str_to_bytes,
    bytes_to_longcoding_str,
    get_longcoding_bit,
    set_longcoding_bit,
    update_longcoding_bytes,
    prepare_coding_write_payload,
)


def test_longcoding_conversion_and_bits():
    s = '01 23 45 67 89 AB CD EF'
    b = longcoding_str_to_bytes(s)
    assert bytes_to_longcoding_str(b) == '0123456789ABCDEF'
    # test bit get/set
    b2 = set_longcoding_bit(b, 0, 0, 1)
    assert get_longcoding_bit(b2, 0, 0) == 1
    b3 = set_longcoding_bit(b2, 0, 0, 0)
    assert get_longcoding_bit(b3, 0, 0) == 0


def test_update_and_prepare_payload():
    s = '00 00 00 00'
    b = longcoding_str_to_bytes(s)
    b2 = update_longcoding_bytes(b, ((0, 1, 1), (3, 7, 1)))
    assert get_longcoding_bit(b2, 0, 1) == 1
    assert get_longcoding_bit(b2, 3, 7) == 1
    payload = prepare_coding_write_payload('F190', b2)
    assert payload.startswith('2EF190')
