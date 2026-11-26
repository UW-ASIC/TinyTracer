POS_FRAC = 7
DIR_FRAC = 14
WORD_MASK = 0xFFFF


def encode_fixed(value: float, frac: int):
    scaled = round(value * (1 << frac))
    if not -32768 <= scaled <= 32767:
        raise ValueError(f"{value} cannot fit in Q{16-frac}.{frac}")
    return scaled & WORD_MASK


def decode_fixed(word: int, frac: int):
    word &= WORD_MASK
    signed = word - 65536 if (word & 0x8000) else word
    return signed / (1 << frac)


def pack_vec3(x: float, y: float, z: float, frac: int):
    return (encode_fixed(z, frac) << 32) | (encode_fixed(y, frac) << 16) | encode_fixed(x, frac)


def unpack_vec3(value: int, frac: int):
    return tuple(decode_fixed(value >> shift, frac) for shift in (0, 16, 32))


def reflect(direction, normal):
    dot = sum(a * b for a, b in zip(direction, normal))
    return tuple(d - 2 * dot * n for d, n in zip(direction, normal))
