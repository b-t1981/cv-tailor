"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="max-w-md rounded-xl border border-red-200 bg-white p-6 text-center shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-slate-900">Erreur de chargement</h2>
        <p className="mb-4 text-sm text-slate-600">
          Rechargez la page. Si le problème persiste, relancez avec{" "}
          <code className="rounded bg-slate-100 px-1">npm run start:prod</code> dans le dossier frontend.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Réessayer
        </button>
      </div>
    </div>
  );
}
