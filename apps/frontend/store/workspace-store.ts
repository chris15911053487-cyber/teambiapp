"use client";

import { create } from "zustand";

export type TasksBundle = {
  name: string;
  tasks: unknown[];
  stages?: unknown[];
  stage_map?: Record<string, string>;
};

export type WorkspaceState = {
  org: Record<string, unknown> | null;
  projects: unknown[] | null;
  tasksByProject: Record<string, TasksBundle> | null;
  worktimeByTask: Record<string, unknown> | null;
  setOrg: (o: Record<string, unknown> | null) => void;
  setProjects: (p: unknown[] | null) => void;
  setTasksByProject: (t: Record<string, TasksBundle> | null) => void;
  setWorktimeByTask: (w: Record<string, unknown> | null) => void;
  reset: () => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  org: null,
  projects: null,
  tasksByProject: null,
  worktimeByTask: null,
  setOrg: (o) => set({ org: o }),
  setProjects: (p) => set({ projects: p }),
  setTasksByProject: (t) => set({ tasksByProject: t }),
  setWorktimeByTask: (w) => set({ worktimeByTask: w }),
  reset: () =>
    set({ org: null, projects: null, tasksByProject: null, worktimeByTask: null }),
}));
