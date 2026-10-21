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

  it("keeps the mounted draft when reauthentication requires renewed consent", async () => {
    let verified = false;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ user_id: "user-1", status: "ACTIVE", consent_required: false });
      if (url === "/api/v1/auth/otp/request") return response({ status: "challenge_requested" }, 202);
      if (url === "/api/v1/auth/otp/verify") {
        verified = true;
        return response({ user_id: "user-1", status: "ACTIVE", consent_required: true });
      }
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: verified ? "csrf-new" : "csrf-old" });
      if (url === "/api/v1/privacy/notice") return response({
        terms_version: "terms-v2", privacy_version: "privacy-v2",
        legal_review_status: "APPROVED", data_inventory_version: "v2",
      });
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><label>Draft<input defaultValue="kept" /></label></AuthProvider>);
    const draft = await screen.findByLabelText("Draft");
    fireEvent.change(draft, { target: { value: "unsaved private note" } });
    window.dispatchEvent(new Event("relapaw:session-expired"));
    fireEvent.change(await screen.findByLabelText("受邀邮箱"), { target: { value: "owner@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    fireEvent.change(await screen.findByLabelText("一次性验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByRole("heading", { name: "开始前，请确认数据约定" })).toBeInTheDocument();
    expect(screen.getByLabelText("Draft")).toHaveValue("unsaved private note");
  });

  it("separates successful OTP verification from recoverable CSRF bootstrap failure", async () => {
    let csrfAttempts = 0;
    let verified = false;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return verified
        ? response({ user_id: "user-1", status: "ACTIVE", consent_required: false })
        : response({ error: { code: "AUTHENTICATION_REQUIRED" } }, 401);
      if (url === "/api/v1/auth/otp/request") return response({ status: "challenge_requested" }, 202);
      if (url === "/api/v1/auth/otp/verify") {
        verified = true;
        return response({ user_id: "user-1", status: "ACTIVE", consent_required: false });
      }
      if (url === "/api/v1/auth/csrf") {
        csrfAttempts += 1;
        return csrfAttempts === 1 ? response({}, 503) : response({ csrf_token: "csrf-recovered" });
      }
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><p>private space</p></AuthProvider>);
    fireEvent.change(await screen.findByLabelText("受邀邮箱"), { target: { value: "owner@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    fireEvent.change(await screen.findByLabelText("一次性验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByRole("heading", { name: "安全会话尚未就绪" })).toBeInTheDocument();
    expect(screen.queryByText("验证码无效或已过期，请重新输入。")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重试安全初始化" }));
    expect(await screen.findByText("private space")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([input]) => String(input) === "/api/v1/auth/otp/verify")).toHaveLength(1);
  });

  it("returns a preserved draft to reauthentication when bootstrap retry finds an expired session", async () => {
    let sessionChecks = 0;
    let csrfChecks = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") {
        sessionChecks += 1;
        return sessionChecks === 1
          ? response({ user_id: "user-1", status: "ACTIVE", consent_required: false })
          : response({ error: { code: "AUTHENTICATION_REQUIRED" } }, 401);
      }
      if (url === "/api/v1/auth/otp/request") return response({ status: "challenge_requested" }, 202);
      if (url === "/api/v1/auth/otp/verify") return response({ user_id: "user-1", status: "ACTIVE", consent_required: false });
      if (url === "/api/v1/auth/csrf") {
        csrfChecks += 1;
        return csrfChecks === 2 ? response({}, 503) : response({ csrf_token: `csrf-${csrfChecks}` });
      }
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><label>Draft<input defaultValue="kept" /></label></AuthProvider>);
    const draft = await screen.findByLabelText("Draft");
    fireEvent.change(draft, { target: { value: "unsaved private note" } });
    window.dispatchEvent(new Event("relapaw:session-expired"));
    fireEvent.change(await screen.findByLabelText("受邀邮箱"), { target: { value: "owner@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    fireEvent.change(await screen.findByLabelText("一次性验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByRole("heading", { name: "安全会话尚未就绪" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重试安全初始化" }));
    expect(await screen.findByRole("heading", { name: "会话已过期" })).toBeInTheDocument();
    expect(screen.getByLabelText("Draft")).toHaveValue("unsaved private note");
  });

  it("allows only one bootstrap retry while session recovery is in flight", async () => {
    let verified = false;
    let sessionCalls = 0;
    let csrfCalls = 0;
    let releaseSession: (() => void) | undefined;
    const delayedSession = new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>((resolve) => {
      releaseSession = () => resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ user_id: "user-1", status: "ACTIVE", consent_required: false }),
      });
    });
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") {
        sessionCalls += 1;
        return verified ? delayedSession : response({ error: { code: "AUTHENTICATION_REQUIRED" } }, 401);
      }
      if (url === "/api/v1/auth/otp/request") return response({ status: "challenge_requested" }, 202);
      if (url === "/api/v1/auth/otp/verify") {
        verified = true;
        return response({ user_id: "user-1", status: "ACTIVE", consent_required: false });
      }
      if (url === "/api/v1/auth/csrf") {
        csrfCalls += 1;
        return csrfCalls === 1 ? response({}, 503) : response({ csrf_token: "csrf-recovered" });
      }
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><p>private space</p></AuthProvider>);
    fireEvent.change(await screen.findByLabelText("受邀邮箱"), { target: { value: "owner@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    fireEvent.change(await screen.findByLabelText("一次性验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "登录" }));
    const retry = await screen.findByRole("button", { name: "重试安全初始化" });
    fireEvent.click(retry);
    fireEvent.click(retry);
    expect(sessionCalls).toBe(2);
    expect(screen.getByRole("button", { name: "正在重试…" })).toBeDisabled();
    releaseSession?.();
    expect(await screen.findByText("private space")).toBeInTheDocument();
    expect(csrfCalls).toBe(2);
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

  it("reloads a changed policy version in place without losing the mounted draft", async () => {
    let noticeVersion = 2;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ user_id: "user-1", status: "ACTIVE", consent_required: false });
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: "csrf-consent" });
      if (url === "/api/v1/privacy/notice") return response({
        terms_version: `terms-v${noticeVersion}`, privacy_version: `privacy-v${noticeVersion}`,
        legal_review_status: "APPROVED", data_inventory_version: `v${noticeVersion}`,
      });
      if (url === "/api/v1/pets") return response({ error: { code: "CONSENT_REQUIRED" } }, 403);
      if (url === "/api/v1/privacy/consent") {
        noticeVersion = 3;
        return response({ error: { code: "POLICY_VERSION_CHANGED", message: "changed" } }, 409);
      }
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><label>Draft<input defaultValue="kept" /></label><button onClick={() => void createPet({ name: "Mochi", species: "cat" }).catch(() => undefined)}>write</button></AuthProvider>);
    const draft = await screen.findByLabelText("Draft");
    fireEvent.change(draft, { target: { value: "unsaved note" } });
    fireEvent.click(screen.getByRole("button", { name: "write" }));
    await screen.findByText(/条款版本：terms-v2/);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "接受并继续" }));
    expect(await screen.findByText(/条款版本：terms-v3/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("政策版本已更新");
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    expect(screen.getByLabelText("Draft")).toHaveValue("unsaved note");
  });

  it("clears a stale policy acceptance when version reload fails", async () => {
    let noticeCalls = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/auth/session") return response({ user_id: "user-1", status: "ACTIVE", consent_required: true });
      if (url === "/api/v1/auth/csrf") return response({ csrf_token: "csrf-consent" });
      if (url === "/api/v1/privacy/notice") {
        noticeCalls += 1;
        if (noticeCalls === 1) return response({ terms_version: "terms-v2", privacy_version: "privacy-v2", legal_review_status: "APPROVED", data_inventory_version: "v2" });
        if (noticeCalls === 2) return response({}, 503);
        return response({ terms_version: "terms-v3", privacy_version: "privacy-v3", legal_review_status: "APPROVED", data_inventory_version: "v3" });
      }
      if (url === "/api/v1/privacy/consent") return response({ error: { code: "POLICY_VERSION_CHANGED" } }, 409);
      return response({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><p>private space</p></AuthProvider>);
    await screen.findByText(/条款版本：terms-v2/);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "接受并继续" }));
    expect(await screen.findByRole("button", { name: "重新载入政策" })).toBeInTheDocument();
    expect(screen.queryByText(/条款版本：terms-v2/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "接受并继续" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "重新载入政策" }));
    expect(await screen.findByText(/条款版本：terms-v3/)).toBeInTheDocument();
  });
});
