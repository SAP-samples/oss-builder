otError Dtls::Start(bool             aClient,
                    ConnectedHandler aConnectedHandler,
                    ReceiveHandler   aReceiveHandler,
                    SendHandler      aSendHandler,
                    void *           aContext)
{
    int rval;

    // do not handle new connection before guard time expired
    VerifyOrExit(mState == kStateStopped, rval = MBEDTLS_ERR_SSL_TIMEOUT);

    mbedtls_ssl_init(&mSsl);
    mbedtls_ssl_config_init(&mConf);
    mbedtls_ctr_drbg_init(&mCtrDrbg);
    mbedtls_entropy_init(&mEntropy);
#if OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE
#ifdef MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED
    mbedtls_x509_crt_init(&mCaChain);
    mbedtls_x509_crt_init(&mOwnCert);
    mbedtls_pk_init(&mPrivateKey);
#endif // MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED
#endif // OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE

    rval = mbedtls_entropy_add_source(&mEntropy, &Dtls::HandleMbedtlsEntropyPoll, NULL, MBEDTLS_ENTROPY_MIN_PLATFORM,
                                      MBEDTLS_ENTROPY_SOURCE_STRONG);
    VerifyOrExit(rval == 0);

    {
        otExtAddress eui64;
        otPlatRadioGetIeeeEui64(&GetInstance(), eui64.m8);
        rval = mbedtls_ctr_drbg_seed(&mCtrDrbg, mbedtls_entropy_func, &mEntropy, eui64.m8, sizeof(eui64));
        VerifyOrExit(rval == 0);
    }

    rval = mbedtls_ssl_config_defaults(&mConf, aClient ? MBEDTLS_SSL_IS_CLIENT : MBEDTLS_SSL_IS_SERVER,
                                       MBEDTLS_SSL_TRANSPORT_DATAGRAM, MBEDTLS_SSL_PRESET_DEFAULT);
    VerifyOrExit(rval == 0);

#if OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE
    if (mVerifyPeerCertificate && mCipherSuites[0] == MBEDTLS_TLS_ECDHE_ECDSA_WITH_AES_128_CCM_8)
    {
        mbedtls_ssl_conf_authmode(&mConf, MBEDTLS_SSL_VERIFY_REQUIRED);
    }
    else
    {
        mbedtls_ssl_conf_authmode(&mConf, MBEDTLS_SSL_VERIFY_NONE);
    }
#else
    OT_UNUSED_VARIABLE(mVerifyPeerCertificate);
#endif // OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE

    mbedtls_ssl_conf_rng(&mConf, mbedtls_ctr_drbg_random, &mCtrDrbg);
    mbedtls_ssl_conf_min_version(&mConf, MBEDTLS_SSL_MAJOR_VERSION_3, MBEDTLS_SSL_MINOR_VERSION_3);
    mbedtls_ssl_conf_max_version(&mConf, MBEDTLS_SSL_MAJOR_VERSION_3, MBEDTLS_SSL_MINOR_VERSION_3);
    mbedtls_ssl_conf_ciphersuites(&mConf, mCipherSuites);
    mbedtls_ssl_conf_export_keys_cb(&mConf, HandleMbedtlsExportKeys, this);
    mbedtls_ssl_conf_handshake_timeout(&mConf, 8000, 60000);
    mbedtls_ssl_conf_dbg(&mConf, HandleMbedtlsDebug, this);

#if OPENTHREAD_ENABLE_BORDER_AGENT || OPENTHREAD_ENABLE_COMMISSIONER || OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE
    if (!aClient)
    {
        mbedtls_ssl_cookie_init(&mCookieCtx);

        rval = mbedtls_ssl_cookie_setup(&mCookieCtx, mbedtls_ctr_drbg_random, &mCtrDrbg);
        VerifyOrExit(rval == 0);

        mbedtls_ssl_conf_dtls_cookies(&mConf, mbedtls_ssl_cookie_write, mbedtls_ssl_cookie_check, &mCookieCtx);
    }
#endif // OPENTHREAD_ENABLE_BORDER_AGENT || OPENTHREAD_ENABLE_COMMISSIONER || OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE

    rval = mbedtls_ssl_setup(&mSsl, &mConf);
    VerifyOrExit(rval == 0);

    mbedtls_ssl_set_bio(&mSsl, this, &Dtls::HandleMbedtlsTransmit, HandleMbedtlsReceive, NULL);
    mbedtls_ssl_set_timer_cb(&mSsl, this, &Dtls::HandleMbedtlsSetTimer, HandleMbedtlsGetTimer);

    if (mCipherSuites[0] == MBEDTLS_TLS_ECJPAKE_WITH_AES_128_CCM_8)
    {
        rval = mbedtls_ssl_set_hs_ecjpake_password(&mSsl, mPsk, mPskLength);
    }
#if OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE
    else
    {
        rval = SetApplicationCoapSecureKeys();
    }
#endif // OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE
    VerifyOrExit(rval == 0);

    mConnectedHandler = aConnectedHandler;
    mReceiveHandler   = aReceiveHandler;
    mSendHandler      = aSendHandler;
    mContext          = aContext;
    mReceiveMessage   = NULL;
    mMessageSubType   = Message::kSubTypeNone;
    mState            = kStateConnecting;

    if (mCipherSuites[0] == MBEDTLS_TLS_ECJPAKE_WITH_AES_128_CCM_8)
    {
        otLogInfoMeshCoP("DTLS started");
    }
#if OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE
    else
    {
        otLogInfoCoap("Application Coap Secure DTLS started");
    }
#endif // OPENTHREAD_ENABLE_APPLICATION_COAP_SECURE

    Process();

exit:
    if (rval != 0)
    {
        FreeMbedtls();
    }

    return MapError(rval);
}