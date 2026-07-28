import type { Metadata } from "next";
import "./globals.css";
import { AssistantPanel } from "@foundry/ui";
import EvalNav from "../components/EvalNav";
import FoundryAccessGate from "../components/FoundryAccessGate";

export const metadata: Metadata = {
  title: "ZoidLab Eval",
  description: "AI evaluation lab — is this AI good enough to ship? Judge answers against criteria.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-bg text-ink">
        <EvalNav />
        <AssistantPanel app="Eval" />
        <main className="mx-auto w-full max-w-[1320px] px-5">
          <FoundryAccessGate packageLabel="Foundry Package 09">{children}</FoundryAccessGate>
        </main>
        <footer className="mx-auto mt-20 w-full max-w-[1320px] border-t border-line px-5 py-8 text-[12px] text-faint">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>ZoidLab Eval · Foundry Package 09 · Is this AI good enough to ship?</span>
            <span className="flex gap-4"><a href="https://foundry.zoidlab.ai" className="hover:text-dim">Foundry</a><a href="https://zoidlab.ai" className="hover:text-dim">zoidlab.ai</a></span>
          </div>
        </footer>
      </body>
    </html>
  );
}
