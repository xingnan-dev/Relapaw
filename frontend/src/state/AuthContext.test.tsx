import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./AuthContext";
import { createPet, setCsrfToken } from "../api";

function response(data: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(data) });
}

describe("AuthProvider", () => {
  beforeEach(() => { vi.restoreAllMocks(); setCsrfToken(null); });

  it("restores a cookie session and bootstraps a bound CSRF token", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ user_id: "user-1", status: "ACTIVE" });
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: "csrf-1" });
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><p>private space</p></AuthProvider>);
    expect(await screen.findByText("private space")).toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([, init]) => init?.credentials === "include")).toBe(true);
  });

  it("attaches the session-bound CSRF token to business writes", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ user_id: "user-1", status: "ACTIVE" });
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: "csrf-write" });
      if (url === "/api/v1/pets") return response({ id: 1 }, 201);
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><button onClick={() => void createPet({ name: "Mochi", species: "cat" })}>write</button></AuthProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "write" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input) === "/api/v1/pets")).toBe(true));
    const call = fetchMock.mock.calls.find(([input]) => String(input) === "/api/v1/pets");
    expect(new Headers(call?.[1]?.headers).get("X-CSRF-Token")).toBe("csrf-write");
  });

  it("shows invited login and completes the two-step challenge without revealing membership", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ error: { code: "AUTHENTICATION_REQUIRED" } }, 401);
      if (url === "/api/v1/auth/otp/request") return response({ status: "challenge_requested" }, 202);
      if (url === "/api/v1/auth/otp/verify") return response({ user_id: "user-1", status: "ACTIVE" });
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: "csrf-1" });
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><p>private space</p></AuthProvider>);
    fireEvent.change(await screen.findByLabelText("受邀邮箱"), { target: { value: "owner@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    fireEvent.change(await screen.findByLabelText("一次性验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByText("private space")).toBeInTheDocument();
  });

  it("keeps mounted form state when the session expires and resumes after login", async () => {
    let sessionChecks = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") {
        sessionChecks += 1;
        return response({ user_id: "user-1", status: "ACTIVE" });
      }
      if (url === "/api/v1/auth/otp/verify") return response({ user_id: "user-1", status: "ACTIVE" });
      if (url === "/api/v1/auth/otp/request") return response({ status: "challenge_requested" }, 202);
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: `csrf-${sessionChecks}` });
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><label>Draft<input defaultValue="kept draft" /></label></AuthProvider>);
    const draft = await screen.findByLabelText("Draft");
    fireEvent.change(draft, { target: { value: "unsaved private note" } });
    window.dispatchEvent(new Event("relapaw:session-expired"));
    expect(await screen.findByRole("heading", { name: "会话已过期" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("受邀邮箱"), { target: { value: "owner@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    fireEvent.change(await screen.findByLabelText("一次性验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    await waitFor(() => expect(screen.getByLabelText("Draft")).toHaveValue("unsaved private note"));
  });

  it("moves an active session into versioned consent without losing mounted draft state", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ user_id: "user-1", status: "ACTIVE", consent_required: false });
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: "csrf-consent" });
      if (url === "/api/v1/privacy/notice") return response({
        terms_version: "terms-v2", privacy_version: "privacy-v2",
        legal_review_status: "APPROVED", data_inventory_version: "v1",
      });
      if (url === "/api/v1/pets") return response({ error: { code: "CONSENT_REQUIRED", message: "Consent required" } }, 403);
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><label>Draft<input defaultValue="kept" /></label><button onClick={() => void createPet({ name: "Mochi", species: "cat" }).catch(() => undefined)}>write</button></AuthProvider>);
    const draft = await screen.findByLabelText("Draft");
    fireEvent.change(draft, { target: { value: "unsaved note" } });
    fireEvent.click(screen.getByRole("button", { name: "write" }));
    expect(await screen.findByRole("heading", { name: "开始前，请确认数据约定" })).toBeInTheDocument();
    expect(screen.getByLabelText("Draft")).toHaveValue("unsaved note");
  });
});
