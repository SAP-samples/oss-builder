otError CoapSecure::Process(int argc, char *argv[])
{
    otError error           = OT_ERROR_NONE;
    bool    mVerifyPeerCert = true;
    long    value;

    VerifyOrExit(argc > 0, error = OT_ERROR_INVALID_ARGS);

    if (strcmp(argv[0], "start") == 0)
    {
        if (argc > 1)
        {
            if (strcmp(argv[1], "false") == 0)
            {
                mVerifyPeerCert = false;
            }
            else if (strcmp(argv[1], "true") != 0)
            {
                ExitNow(error = OT_ERROR_INVALID_ARGS);
            }
        }
        otCoapSecureSetSslAuthMode(mInterpreter.mInstance, mVerifyPeerCert);
        SuccessOrExit(error = otCoapSecureStart(mInterpreter.mInstance, OT_DEFAULT_COAP_SECURE_PORT, this));
        otCoapSecureSetClientConnectedCallback(mInterpreter.mInstance, &CoapSecure::HandleClientConnect, this);
#if CLI_COAP_SECURE_USE_COAP_DEFAULT_HANDLER
        otCoapSecureSetDefaultHandler(mInterpreter.mInstance, &CoapSecure::DefaultHandle, this);
#endif // CLI_COAP_SECURE_USE_COAP_DEFAULT_HANDLER
#ifdef MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED
        if (mUseCertificate)
        {
            mInterpreter.mServer->OutputFormat("Verify Peer Certificate: %s. Coap Secure service started: ",
                                               mVerifyPeerCert ? "true" : "false");
        }
#endif // MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED
    }
    else if (strcmp(argv[0], "set") == 0)
    {
        if (argc > 1)
        {
            if (strcmp(argv[1], "psk") == 0)
            {
                if (argc > 3)
                {
                    size_t length;

                    length = strlen(argv[2]);
                    VerifyOrExit(length <= sizeof(mPsk), error = OT_ERROR_INVALID_ARGS);
                    mPskLength = static_cast<uint8_t>(length);
                    memcpy(mPsk, argv[2], mPskLength);

                    length = strlen(argv[3]);
                    VerifyOrExit(length <= sizeof(mPskId), error = OT_ERROR_INVALID_ARGS);
                    mPskIdLength = static_cast<uint8_t>(length);
                    memcpy(mPskId, argv[3], mPskIdLength);

                    SuccessOrExit(
                        error = otCoapSecureSetPsk(mInterpreter.mInstance, mPsk, mPskLength, mPskId, mPskIdLength));
                    mUseCertificate = false;
                    mInterpreter.mServer->OutputFormat("Coap Secure set PSK: ");
                }
                else
                {
                    ExitNow(error = OT_ERROR_INVALID_ARGS);
                }
            }
            else if (strcmp(argv[1], "x509") == 0)
            {
#ifdef MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED
                SuccessOrExit(error = otCoapSecureSetCertificate(
                                  mInterpreter.mInstance, (const uint8_t *)OT_CLI_COAPS_X509_CERT,
                                  sizeof(OT_CLI_COAPS_X509_CERT), (const uint8_t *)OT_CLI_COAPS_PRIV_KEY,
                                  sizeof(OT_CLI_COAPS_PRIV_KEY)));

                SuccessOrExit(error = otCoapSecureSetCaCertificateChain(
                                  mInterpreter.mInstance, (const uint8_t *)OT_CLI_COAPS_TRUSTED_ROOT_CERTIFICATE,
                                  sizeof(OT_CLI_COAPS_TRUSTED_ROOT_CERTIFICATE)));
                mUseCertificate = true;

                mInterpreter.mServer->OutputFormat("Coap Secure set own .X509 certificate: ");
#else
                ExitNow(error = OT_ERROR_DISABLED_FEATURE);
#endif // MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED
            }
            else
            {
                ExitNow(error = OT_ERROR_INVALID_ARGS);
            }
        }
        else
        {
            ExitNow(error = OT_ERROR_INVALID_ARGS);
        }
    }
    else if (strcmp(argv[0], "connect") == 0)
    {
        // Destination IPv6 address
        if (argc > 1)
        {
            otSockAddr sockaddr;

            memset(&sockaddr, 0, sizeof(sockaddr));
            SuccessOrExit(error = otIp6AddressFromString(argv[1], &sockaddr.mAddress));
            sockaddr.mPort    = OT_DEFAULT_COAP_SECURE_PORT;
            sockaddr.mScopeId = OT_NETIF_INTERFACE_ID_THREAD;

            // check for port specification
            if (argc > 2)
            {
                error = Interpreter::ParseLong(argv[2], value);
                SuccessOrExit(error);
                sockaddr.mPort = static_cast<uint16_t>(value);
            }

            SuccessOrExit(
                error = otCoapSecureConnect(mInterpreter.mInstance, &sockaddr, &CoapSecure::HandleClientConnect, this));
            mInterpreter.mServer->OutputFormat("Coap Secure connect: ");
        }
        else
        {
            ExitNow(error = OT_ERROR_INVALID_ARGS);
        }
    }
    else if (strcmp(argv[0], "resource") == 0)
    {
        mResource.mUriPath = mUriPath;
        mResource.mContext = this;
        mResource.mHandler = &CoapSecure::HandleServerResponse;

        if (argc > 1)
        {
            strlcpy(mUriPath, argv[1], kMaxUriLength);
            SuccessOrExit(error = otCoapSecureAddResource(mInterpreter.mInstance, &mResource));
        }

        mInterpreter.mServer->OutputFormat("Resource name is '%s': ", mResource.mUriPath);
    }
    else if (strcmp(argv[0], "disconnect") == 0)
    {
        SuccessOrExit(error = otCoapSecureDisconnect(mInterpreter.mInstance));
    }
    else if (strcmp(argv[0], "stop") == 0)
    {
        if (otCoapSecureIsConnectionActive(mInterpreter.mInstance))
        {
            error         = otCoapSecureDisconnect(mInterpreter.mInstance);
            mShutdownFlag = true;
        }
        else
        {
            SuccessOrExit(error = Stop());
        }
    }
    else if (strcmp(argv[0], "help") == 0)
    {
        mInterpreter.mServer->OutputFormat("CLI CoAPS help:\r\n\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps start (false)'                               "
                                           ": start coap secure service, false disable peer cert verification\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps set psk <psk> <client id>'                   "
                                           ": set Preshared Key and Client Identity (Ciphersuite PSK_AES128)\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps set x509'                                    "
                                           ": set X509 Cert und Private Key (Ciphersuite ECDHE_ECDSA_AES128)\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps connect <servers ipv6 addr> (port)'          "
                                           ": start dtls session with a server\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps get' 'coaps put' 'coaps post' 'coaps delete' "
                                           ": interact with coap resource from server, ipv6 is not need as client\r\n");
        mInterpreter.mServer->OutputFormat(
            "    >> args:(ipv6_addr_srv) <coap_src> and, if you have payload: <con> <payload>\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps resource <uri>'                              "
                                           ": add a coap server resource with 'helloWorld' as content.\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps disconnect'                                  "
                                           ": stop dtls session with a server\r\n");
        mInterpreter.mServer->OutputFormat(">'coaps stop'                                        "
                                           ": stop coap secure service\r\n");
        mInterpreter.mServer->OutputFormat("\r\n legend: <>: must, (): opt                       "
                                           "\r\n");
        mInterpreter.mServer->OutputFormat("\r\n");
    }
    else
    {
        error = ProcessRequest(argc, argv);
    }

exit:
    return error;
}