# Sur5 Bundled Fonts

This directory contains bundled fonts for the Sur5 application.
When fonts are present, they are automatically loaded and used as the primary UI font.

## IBM Plex Sans (Recommended)

IBM Plex Sans is the primary UI font - a distinctive, tech-forward font with excellent readability.

### Quick Download

1. Visit: https://fonts.google.com/specimen/IBM+Plex+Sans
2. Click "Download family" button (top right)
3. Extract the ZIP file
4. Copy these TTF files to this `fonts/` directory:
   - `IBMPlexSans-Regular.ttf`
   - `IBMPlexSans-Medium.ttf`
   - `IBMPlexSans-SemiBold.ttf`
   - `IBMPlexSans-Italic.ttf`

### Alternative: Direct from IBM

Download from the official IBM Plex repository:
https://github.com/IBM/plex/releases

### License

IBM Plex Sans is licensed under the SIL Open Font License 1.1.
See `OFL.txt` in this directory or: https://github.com/IBM/plex/blob/master/LICENSE.txt

## Other Supported Fonts

The application will also use these fonts if installed on your system:
- Atkinson Hyperlegible (accessibility-focused)
- Source Sans Pro (Adobe's elegant font)
- Fira Sans (Mozilla's humanist sans-serif)
- Outfit, DM Sans, Lexend, Nunito

## No Fonts?

If no bundled fonts are present, the application gracefully falls back to:
- Windows: Segoe UI
- macOS: SF Pro Display / Helvetica Neue
- Linux: Ubuntu / Cantarell / Noto Sans
