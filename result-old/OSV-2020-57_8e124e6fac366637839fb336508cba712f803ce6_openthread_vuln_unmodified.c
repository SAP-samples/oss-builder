otError Leader::Validate(const uint8_t *aTlvs, uint8_t aTlvsLength, uint16_t aRloc16)
{
    // Validate that the `aTlvs` contains well-formed TLVs, sub-TLVs,
    // and entries all matching `aRloc16` (no other entry for other
    // RLOCs and no duplicates TLVs).

    otError               error = OT_ERROR_NONE;
    const NetworkDataTlv *end   = reinterpret_cast<const NetworkDataTlv *>(aTlvs + aTlvsLength);

    for (const NetworkDataTlv *cur = reinterpret_cast<const NetworkDataTlv *>(aTlvs); cur < end; cur = cur->GetNext())
    {
        VerifyOrExit((cur + 1) <= end && cur->GetNext() <= end, error = OT_ERROR_PARSE);

        switch (cur->GetType())
        {
        case NetworkDataTlv::kTypePrefix:
        {
            const PrefixTlv *prefix = static_cast<const PrefixTlv *>(cur);

            VerifyOrExit(prefix->IsValid(), error = OT_ERROR_PARSE);

            // Ensure there is no duplicate Prefix TLVs with same prefix.
            VerifyOrExit(prefix == FindPrefix(prefix->GetPrefix(), prefix->GetPrefixLength(), aTlvs, aTlvsLength),
                         error = OT_ERROR_PARSE);

            SuccessOrExit(error = ValidatePrefix(*prefix, aRloc16));
            break;
        }

        case NetworkDataTlv::kTypeService:
        {
            const ServiceTlv *service = static_cast<const ServiceTlv *>(cur);

            VerifyOrExit(service->IsValid(), error = OT_ERROR_PARSE);

            // Ensure there is no duplicate Service TLV with same
            // Enterprise Number and Service Data.
            VerifyOrExit(service == FindService(service->GetEnterpriseNumber(), service->GetServiceData(),
                                                service->GetServiceDataLength(), aTlvs, aTlvsLength),
                         error = OT_ERROR_PARSE);

            SuccessOrExit(error = ValidateService(*service, aRloc16));
            break;
        }

        default:
            break;
        }
    }

exit:
    return error;
}