"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SessionState = {
  teambitionToken: string | null;
  tenantId: string | null;
  companyName: string | null;
  sessionJwt: string | null;
  debugEnabled: boolean;
  setAuth: (payload: {
    teambition_access_token: string;
    tenant_id: string;
    company_name: string;
    session_jwt?: string | null;
  }) => void;
  setDebugEnabled: (v: boolean) => void;
  clear: () => void;
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      teambitionToken: null,
      tenantId: null,
      companyName: null,
      sessionJwt: null,
      debugEnabled: false,
      setAuth: (payload) =>
        set({
          teambitionToken: payload.session_jwt || payload.teambition_access_token,
          tenantId: payload.tenant_id,
          companyName: payload.company_name,
          sessionJwt: payload.session_jwt || null,
        }),
      setDebugEnabled: (v) => set({ debugEnabled: v }),
      clear: () =>
        set({
          teambitionToken: null,
          tenantId: null,
          companyName: null,
          sessionJwt: null,
        }),
    }),
    { name: "teambition-session" },
  ),
);
