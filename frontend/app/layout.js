import "./globals.css";

export const metadata = {
  title: "MediSprache - Clinical Dictation AI",
  description: "Upload German medical dictation audio and generate structured clinical summaries with AI-powered transcription.",
  keywords: ["medical dictation", "clinical transcription", "German medical AI", "healthcare documentation"],
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f766e",
};

export default function RootLayout({ children }) {
  return (
    <html lang="de">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
