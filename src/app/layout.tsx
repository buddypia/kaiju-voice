import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { Noto_Sans_JP } from 'next/font/google';
import './globals.css';

const geist = Geist({
  subsets: ['latin'],
  variable: '--font-geist',
  display: 'swap',
});

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
});

const notoSansJP = Noto_Sans_JP({
  subsets: ['latin'],
  variable: '--font-noto-sans-jp',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL ?? 'http://localhost:3000'),
  title: 'KAIJU VOICE — 声で戦え、怪獣バトル',
  description: '声で怪獣を操る2Pバトルゲーム。Gemini AI がリアルタイムで声の創造性を判定！',
  icons: {
    icon: '/images/favicon.png',
    apple: '/images/favicon.png',
  },
  openGraph: {
    title: 'KAIJU VOICE — 声で戦え、怪獣バトル',
    description: '声で怪獣を操る2Pバトルゲーム。Gemini AI がリアルタイムで声の創造性を判定！',
    images: [{ url: '/images/og-image.png', width: 1536, height: 1024 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'KAIJU VOICE — 声で戦え、怪獣バトル',
    description: '声で怪獣を操る2Pバトルゲーム。Gemini AI がリアルタイムで声の創造性を判定！',
    images: ['/images/og-image.png'],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="ja"
      className={`dark ${geist.variable} ${geistMono.variable} ${notoSansJP.variable}`}
      style={{ colorScheme: 'dark' }}
    >
      <head>
        <meta name="theme-color" content="#0b1120" />
      </head>
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
        >
          メインコンテンツへスキップ
        </a>
        <main id="main-content">{children}</main>
      </body>
    </html>
  );
}
