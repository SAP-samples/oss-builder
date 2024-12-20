exif_mnote_data_apple_identify(const ExifData *ed, const ExifEntry *e) {
    int variant;

    if (!strcmp((const char *) e->data, "Apple iOS")) {
        variant = 1;
    } else {
        variant = 0;
    }

    return variant;
}