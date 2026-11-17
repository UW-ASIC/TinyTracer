WLEN = 16
MASK = (1 << WLEN) - 1

MAX_VAL = (1 << (WLEN - 1)) - 1
MIN_VAL = -(1 << (WLEN - 1))

ALU_ADD = 0b000
ALU_SUB = 0b001
ALU_EQ = 0b010
ALU_NE = 0b011
ALU_LT = 0b100
ALU_GE = 0b101


def to_signed(value):
    value &= MASK

    if value & (1 << (WLEN - 1)):
        return value - (1 << WLEN)

    return value


def saturate(value):
    return max(MIN_VAL, min(MAX_VAL, value))


def alu_ref(opcode, a, b):
    a = to_signed(a)
    b = to_signed(b)

    if opcode == ALU_ADD:
        result = saturate(a + b)

    elif opcode == ALU_SUB:
        result = saturate(a - b)

    elif opcode == ALU_EQ:
        result = int(a == b)

    elif opcode == ALU_NE:
        result = int(a != b)

    elif opcode == ALU_LT:
        result = int(a < b)

    elif opcode == ALU_GE:
        result = int(a >= b)

    else:
        raise ValueError(f"Invalid opcode: {opcode}")

    return result & MASK
