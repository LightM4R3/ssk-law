import { defineStore } from "pinia";

import { authApi } from "../services/api";


export const useAuthStore = defineStore("auth", {
  state: () => ({
    account: null,
    initialized: false,
    loading: false,
    error: null,
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.account),
  },

  actions: {
    async ensureCsrfToken() {
      await authApi.getCsrfToken();
    },

    async loadCurrentAccount(options = {}) {
      const silent = Boolean(options.silent);
      if (!silent) this.loading = true;
      this.error = null;
      try {
        const payload = await authApi.getCurrentAccount();
        this.account = payload.account;
        return payload;
      } catch (error) {
        if (error.status !== 401) this.error = error;
        this.account = null;
        return null;
      } finally {
        if (!silent) this.loading = false;
        this.initialized = true;
      }
    },

    async refreshSession() {
      if (!this.account) return null;
      return this.loadCurrentAccount({ silent: true });
    },

    expireSession() {
      this.account = null;
      this.initialized = true;
      this.loading = false;
    },

    async login(id, password) {
      this.loading = true;
      this.error = null;
      try {
        await this.ensureCsrfToken();
        const payload = await authApi.login(id, password);
        this.account = payload.account;
        this.initialized = true;
        return this.account;
      } catch (error) {
        this.account = null;
        this.error = error;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async signup(account) {
      this.loading = true;
      this.error = null;
      try {
        await this.ensureCsrfToken();
        return await authApi.signup(account);
      } catch (error) {
        this.error = error;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async logout() {
      this.loading = true;
      this.error = null;
      try {
        await authApi.logout();
      } finally {
        this.account = null;
        this.loading = false;
        this.initialized = true;
      }
    },
  },
});
