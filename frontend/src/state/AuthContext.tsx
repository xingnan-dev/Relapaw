import { createContext, useContext, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { acceptPrivacyConsent, ApiError, getAuthSession, getCsrfToken, getPrivacyNotice, logout, requestLoginChallenge, setCsrfToken, verifyLoginChallenge, type AuthSession } from "../api";

type AuthStatus = "loading" | "anonymous" | "consent" | "authenticated" | "expired" | "error";

interface AuthValue {
  session: AuthSession | null;
  status: AuthStatus;
  signOut: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<AuthValue>({
  session: null,
  status: "anonymous",
  signOut: async () => undefined,
  retry: () => undefined,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [attempt, setAttempt] = useState(0);
  const [preserveChildrenForConsent, setPreserveChildrenForConsent] = useState(false);

  async function establish(next: AuthSession) {
    const csrf = await getCsrfToken();
    setCsrfToken(csrf.csrf_token);
    setSession(next);
    setStatus(next.consent_required ? "consent" : "authenticated");
  }

  useEffect(() => {
    let active = true;
    setStatus("loading");
    getAuthSession().then(async (next) => {
      if (!active) return;
      const csrf = await getCsrfToken();
      if (!active) return;
      setCsrfToken(csrf.csrf_token);
      setSession(next);
      setStatus(next.consent_required ? "consent" : "authenticated");
    }).catch((error) => {
      if (!active) return;
      setCsrfToken(null);
      setSession(null);
      setStatus(error instanceof ApiError && error.status === 401 ? "anonymous" : "error");
    });
    return () => { active = false; };
  }, [attempt]);

  useEffect(() => {
    const expire = () => {
      if (status === "authenticated" || status === "consent") {
        setCsrfToken(null);
        setStatus("expired");
      }
    };
    window.addEventListener("relapaw:session-expired", expire);
    return () => window.removeEventListener("relapaw:session-expired", expire);
  }, [status]);

  useEffect(() => {
    const requireConsent = () => {
      if (status === "authenticated") {
        setPreserveChildrenForConsent(true);
        setStatus("consent");
      }
    };
    window.addEventListener("relapaw:consent-required", requireConsent);
    return () => window.removeEventListener("relapaw:consent-required", requireConsent);
  }, [status]);

  const value = useMemo<AuthValue>(() => ({
    session,
    status,
    async signOut() {
      const csrf = await getCsrfToken();
      await logout(csrf.csrf_token);
      setCsrfToken(null);
      setSession(null);
      setStatus("anonymous");
    },
    retry: () => setAttempt((value) => value + 1),
  }), [session, status]);

  if (status === "loading") return <AuthContext.Provider value={value}><main className="auth-page"><p role="status">正在恢复安全会话…</p></main></AuthContext.Provider>;
  if (status === "error") return <AuthContext.Provider value={value}><main className="auth-page"><h1>暂时无法连接</h1><p role="alert">无法确认会话状态，请检查网络后重试。</p><button type="button" onClick={value.retry}>重试</button></main></AuthContext.Provider>;
  if (status === "anonymous") return <AuthContext.Provider value={value}><LoginPage onAuthenticated={establish} /></AuthContext.Provider>;
  const consentAccepted = () => {
    void getAuthSession().then(establish).then(() => setPreserveChildrenForConsent(false)).catch(() => setStatus("error"));
  };
  if (status === "consent" && !preserveChildrenForConsent) return <AuthContext.Provider value={value}><ConsentPage onAccepted={consentAccepted} /></AuthContext.Provider>;
  return <AuthContext.Provider value={value}>
    <div hidden={status === "expired" || status === "consent"}>{children}</div>
    {status === "expired" && <LoginPage expired onAuthenticated={establish} />}
    {status === "consent" && <ConsentPage onAccepted={consentAccepted} />}
  </AuthContext.Provider>;
}

function ConsentPage({ onAccepted }: { onAccepted: () => void }) {
  const [notice, setNotice] = useState<Awaited<ReturnType<typeof getPrivacyNotice>> | null>(null);
  const [adult, setAdult] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getPrivacyNotice().then(setNotice).catch(() => setError("无法载入当前政策版本，请稍后重试。")); }, []);
  async function accept() {
    if (!notice || !adult) return;
    setBusy(true); setError(null);
    try { await acceptPrivacyConsent(notice); onAccepted(); }
    catch { setError("接受记录未能保存，请重试。若政策版本已更新，请刷新页面。" ); setBusy(false); }
  }
  return <main className="auth-page"><section className="auth-card" aria-labelledby="consent-title">
    <p className="eyebrow">RELAPAW · PRIVACY</p><h1 id="consent-title">开始前，请确认数据约定</h1>
    <p>Relapaw 会保存你主动提交的宠物资料、观察记录和反馈，用于提供时间线、回看与可撤回的长期记忆。它不提供诊断，也不替代兽医。</p>
    {notice && <p>条款版本：{notice.terms_version}<br/>隐私版本：{notice.privacy_version}<br/>法律审核状态：{notice.legal_review_status === "APPROVED" ? "已批准" : "待审核（生产环境不可启用）"}</p>}
    <label><input type="checkbox" checked={adult} onChange={(event) => setAdult(event.target.checked)} /> 我确认自己是成年宠物主人，并接受当前版本的条款与隐私说明。</label>
    {error && <p role="alert">{error}</p>}
    <button className="primary" type="button" disabled={!notice || !adult || busy} onClick={() => void accept()}>{busy ? "正在保存…" : "接受并继续"}</button>
  </section></main>;
}

function LoginPage({ expired = false, onAuthenticated }: { expired?: boolean; onAuthenticated: (session: AuthSession) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      if (step === "email") {
        await requestLoginChallenge(email);
        setStep("code");
      } else {
        await onAuthenticated(await verifyLoginChallenge(email, code));
      }
    } catch {
      setError(step === "email" ? "暂时无法请求登录验证码，请重试。" : "验证码无效或已过期，请重新输入。");
    } finally { setBusy(false); }
  }

  return <main className="auth-page">
    <section className="auth-card" aria-labelledby="auth-title">
      <p className="eyebrow">RELAPAW · INVITED BETA</p>
      <h1 id="auth-title">{expired ? "会话已过期" : "回到你和它的空间"}</h1>
      <p>{expired ? "你的输入仍保留在本页。重新登录后，请主动重试保存。" : "当前仅向受邀的成年宠物主人开放。"}</p>
      <form onSubmit={submit}>
        <label>受邀邮箱<input type="email" autoComplete="email" required value={email} disabled={step === "code" || busy} onChange={(event) => setEmail(event.target.value)} /></label>
        {step === "code" && <label>一次性验证码<input inputMode="numeric" autoComplete="one-time-code" required value={code} onChange={(event) => setCode(event.target.value)} /></label>}
        {error && <p role="alert">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>{busy ? "请稍候…" : step === "email" ? "获取验证码" : "登录"}</button>
        {step === "code" && <button type="button" disabled={busy} onClick={() => { setStep("email"); setCode(""); }}>更换邮箱</button>}
      </form>
      <p className="safety-note">Relapaw 不诊断，也不替代兽医。出现危险信号时，请及时联系兽医。</p>
    </section>
  </main>;
}

export function useAuth(): AuthValue {
  return useContext(AuthContext);
}
