"use client";
import "./globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import { useState } from "react";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <QueryClientProvider client={queryClient}>
          <Navbar />
          <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
