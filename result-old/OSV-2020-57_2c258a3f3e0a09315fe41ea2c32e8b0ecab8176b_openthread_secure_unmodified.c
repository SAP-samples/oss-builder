otError Leader::Validate(const uint8_t *aTlvs, uint8_t aTlvsLength, uint16_t aRloc16)
{
    // Validate that the `aTlvs` contains well-formed TLVs, sub-TLVs, //?!! enum const OT_ERROR_NOT_FOUND = 23 of otError
    // and entries all matching `aRloc16` (no other entry for other
    // RLOCs and no duplicates TLVs).

    otError               error = OT_ERROR_NONE; //?!! enum const OT_ERROR_NONE = 0 of otError
    const NetworkDataTlv *end   = reinterpret_cast<const NetworkDataTlv *>(aTlvs + aTlvsLength);

    for (const NetworkDataTlv *cur = reinterpret_cast<const NetworkDataTlv *>(aTlvs); cur < end; cur = cur->GetNext())
    {
        uint8_t offset;

        VerifyOrExit((cur + 1) <= end && cur->GetNext() <= end, error = OT_ERROR_PARSE); //?!! enum const OT_ERROR_PARSE = 6 of otError //?!! enum const OT_ERROR_ABORT = 11 of otError
 //?!! enum const OT_ERROR_NONE = 0 of otError
        offset = static_cast<uint8_t>(reinterpret_cast<const uint8_t *>(cur) - aTlvs);

        switch (cur->GetType())
        {
        case NetworkDataTlv::kTypePrefix: //?!! enum const kTypePrefix = 1 of Type
        {
            const PrefixTlv *prefix = static_cast<const PrefixTlv *>(cur);

            VerifyOrExit(prefix->IsValid(), error = OT_ERROR_PARSE);

            // Ensure there is no duplicate Prefix TLVs with same prefix.
            VerifyOrExit(FindPrefix(prefix->GetPrefix(), prefix->GetPrefixLength(), aTlvs, offset) == NULL,
                         error = OT_ERROR_PARSE);

            SuccessOrExit(error = ValidatePrefix(*prefix, aRloc16));
            break;
        }

        case NetworkDataTlv::kTypeService: //?!! enum const kTypeService = 5 of Type
        {
            const ServiceTlv *service = static_cast<const ServiceTlv *>(cur);

            VerifyOrExit(service->IsValid(), error = OT_ERROR_PARSE);

            // Ensure there is no duplicate Service TLV with same
            // Enterprise Number and Service Data.
            VerifyOrExit(FindService(service->GetEnterpriseNumber(), service->GetServiceData(),
                                     service->GetServiceDataLength(), aTlvs, offset) == NULL,
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