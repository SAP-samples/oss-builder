    bool IsValid(void) const
    {
        uint8_t length = GetLength();

        return (length >= sizeof(mFlagsServiceId)) &&
               (length >= kMinLength + (IsThreadEnterprise() ? 0 : sizeof(uint32_t))) && (length >= GetFieldsLength());
    }