import { defineStore } from "pinia";
import { AUTH_USER_EVENT, api, type User } from "../api/client";

const STORAGE_KEY = "lawcompass:user";
type AuthStatus = "idle" | "checking" | "authenticated" | "anonymous" | "unknown";

let bootstrapPromise: Promise<void> | null = null;
let authEventListenerRegistered = false;

export const useSessionStore = defineStore("session", {
  state: () => ({
    user: null as User | null,
    loading: false,
    bootstrapped: false,
    authStatus: "idle" as AuthStatus,
    lastAuthError: ""
  }),
  actions: {
    persistUser(user: User | null) {
      this.user = user;
      if (user) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
        this.authStatus = "authenticated";
      } else {
        localStorage.removeItem(STORAGE_KEY);
        this.authStatus = "anonymous";
      }
    },
    ensureAuthEventListener() {
      if (authEventListenerRegistered || typeof window === "undefined") return;
      authEventListenerRegistered = true;
      window.addEventListener(AUTH_USER_EVENT, (event) => {
        const user = (event as CustomEvent<User | null>).detail ?? null;
        this.persistUser(user);
        this.bootstrapped = true;
        this.lastAuthError = "";
      });
    },
    restoreLocal() {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      try {
        this.user = JSON.parse(raw) as User;
        this.authStatus = "checking";
      } catch {
        this.persistUser(null);
      }
    },
    async bootstrap() {
      if (bootstrapPromise) return bootstrapPromise;
      bootstrapPromise = this.doBootstrap().finally(() => {
        bootstrapPromise = null;
      });
      return bootstrapPromise;
    },
    async doBootstrap() {
      this.ensureAuthEventListener();
      if (this.bootstrapped && this.user) return;

      this.restoreLocal();
      this.loading = true;
      this.authStatus = "checking";
      this.lastAuthError = "";

      try {
        const me = await api.me();
        this.persistUser(me.user);
      } catch (err: any) {
        if (err?.status === 401) {
          this.persistUser(null);
        } else {
          this.authStatus = this.user ? "unknown" : "anonymous";
          this.lastAuthError = err?.message || "";
        }
      } finally {
        this.bootstrapped = true;
        this.loading = false;
      }
    },
    async login(email: string, password: string) {
      this.ensureAuthEventListener();
      this.loading = true;
      try {
        const data = await api.login({ email, password });
        this.persistUser(data.user);
        this.bootstrapped = true;
        this.lastAuthError = "";
      } finally {
        this.loading = false;
      }
    },
    async logout() {
      await api.logout().catch(() => null);
      this.persistUser(null);
      this.bootstrapped = true;
      this.lastAuthError = "";
    }
  }
});
