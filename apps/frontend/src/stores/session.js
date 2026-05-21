import { defineStore } from "pinia";
import { api } from "../api/client";
const STORAGE_KEY = "lawcompass:user";
export const useSessionStore = defineStore("session", {
    state: () => ({
        user: null,
        loading: false,
        bootstrapped: false
    }),
    actions: {
        restoreLocal() {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw)
                return;
            try {
                this.user = JSON.parse(raw);
            }
            catch {
                this.user = null;
            }
        },
        async bootstrap() {
            if (this.bootstrapped)
                return;
            this.restoreLocal();
            try {
                const me = await api.me();
                this.user = me.user;
                localStorage.setItem(STORAGE_KEY, JSON.stringify(me.user));
            }
            catch (err) {
                if (err?.status === 401) {
                    try {
                        const refreshed = await api.refresh();
                        this.user = refreshed.user;
                        localStorage.setItem(STORAGE_KEY, JSON.stringify(refreshed.user));
                    }
                    catch {
                        this.user = null;
                        localStorage.removeItem(STORAGE_KEY);
                    }
                }
            }
            finally {
                this.bootstrapped = true;
            }
        },
        async login(email, password) {
            this.loading = true;
            try {
                const data = await api.login({ email, password });
                this.user = data.user;
                localStorage.setItem(STORAGE_KEY, JSON.stringify(data.user));
            }
            finally {
                this.loading = false;
            }
        },
        async logout() {
            await api.logout().catch(() => null);
            this.user = null;
            localStorage.removeItem(STORAGE_KEY);
            this.bootstrapped = true;
        }
    }
});
