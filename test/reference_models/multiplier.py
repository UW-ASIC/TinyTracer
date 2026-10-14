class multiplier:
    def __init__(self ,WLEN=16):
        self.WLEN = WLEN

    #Python has infinite precision so we need to bitmask to get proper values
    def mask(self,val):
        mask = (1 << self.WLEN) - 1 #All 1 bits    
        return (val & mask);     

    def sign_extend(self, val):
        val = self.mask(val)
        sign_check = (1 << self.WLEN - 1)

        if sign_check & val:
            val = val - (1 << self.WLEN)
            return val

        return val

    def product(self, multiplicand, multiplier,rst_n, req_fmt): #Multiplier takes 2 16-bit inputs(fixed-point) 
        #if multiplier is reset, then expected output is 0
        if(rst_n == 0):
            return self.mask(0)

        signed_multiplicand = self.sign_extend(multiplicand) #ensure proper signed values in python
        signed_multiplier = self.sign_extend(multiplier)

        product_result = signed_multiplicand * signed_multiplier #operation to get 32 bit product

        
        if req_fmt == 0:
            shift = 7 #shift result by 7
        else:
            shift = 14 #shift result by 14

        rounding = 1 << (shift-1) #rounding bias, affects the LSB in front of decimal

        product_result = (product_result + rounding) >> shift

        if product_result > 0x7FFF:
            product_result = 0x7FFF
        elif product_result < -0x8000: 
            product_result = -0x8000


        return self.mask(product_result) #return results

