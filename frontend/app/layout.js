import "./globals.css";

export const metadata = {
  title: "MediSprache",
  description: "Upload German medical dictation audio and get structured JSON.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
