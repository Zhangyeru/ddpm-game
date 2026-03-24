import { useMemo, useState } from "react";
import type { AuthUser, PendingActionKind, ProgressSnapshot } from "../game/types";
import { formatLevelCode } from "../game/levelPresentation";
import { formatSignedScore } from "../game/scorePresentation";

type AuthPanelProps = {
  authBusyAction: Extract<PendingActionKind, "login" | "logout" | "register"> | null;
  authError: string | null;
  authUser: AuthUser | null;
  onClearError: () => void;
  onLogin: (username: string, password: string) => Promise<void>;
  onLogout: () => Promise<void>;
  onRegister: (username: string, password: string) => Promise<void>;
  progression: ProgressSnapshot | null;
};

type AuthMode = "login" | "register";
type ValidationErrors = {
  username?: string;
  password?: string;
  confirmPassword?: string;
};

const USERNAME_PATTERN = /^[A-Za-z0-9_]{3,20}$/;

export function AuthPanel({
  authBusyAction,
  authError,
  authUser,
  onClearError,
  onLogin,
  onLogout,
  onRegister,
  progression
}: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  const isBusy = authBusyAction !== null;
  const currentLevel = progression?.current_level ?? null;
  const panelSummary = useMemo(() => {
    if (!currentLevel) {
      return "登录后保存进度，未登录时仍可直接试玩。";
    }

    return `当前进度：${formatLevelCode(currentLevel.chapter, currentLevel.level)} ${currentLevel.level_title}`;
  }, [currentLevel]);

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setValidationErrors({});
    onClearError();
  }

  function clearValidationError(fieldName: keyof ValidationErrors) {
    setValidationErrors((current) => {
      if (!current[fieldName]) {
        return current;
      }

      const next = { ...current };
      delete next[fieldName];
      return next;
    });
  }

  function validateForm(): ValidationErrors {
    const nextErrors: ValidationErrors = {};

    if (!USERNAME_PATTERN.test(username.trim())) {
      nextErrors.username = "用户名需为 3-20 位，仅可包含字母、数字和下划线。";
    }

    if (password.length < 8) {
      nextErrors.password = "密码至少需要 8 位。";
    }

    if (mode === "register" && confirmPassword !== password) {
      nextErrors.confirmPassword = "两次输入的密码不一致。";
    }

    return nextErrors;
  }

  async function submitForm() {
    const nextErrors = validateForm();
    setValidationErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onClearError();
    if (mode === "login") {
      await onLogin(username.trim(), password);
      return;
    }

    await onRegister(username.trim(), password);
  }

  if (authUser) {
    return (
      <section className="panel landing-panel auth-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">账号存档</p>
            <h2>已登录</h2>
          </div>
          <span className="tool-counter">{authUser.username}</span>
        </div>

        <div className="auth-account-card">
          <strong>{authUser.username}</strong>
          <p>{panelSummary}</p>
          <span>
            {progression
              ? `已完成 ${progression.completed_count}/${progression.total_levels} 关 · 总分 ${formatSignedScore(progression.campaign_total_score)}`
              : "账号进度已保存到当前设备上的服务端数据库。"}
          </span>
        </div>

        <div className="auth-panel__footer">
          <p className="subtle-copy">之后继续闯关时，会直接读取这个账号的关卡进度。</p>
          <button
            className="secondary-button"
            disabled={isBusy}
            onClick={() => {
              void onLogout();
            }}
            type="button"
          >
            {authBusyAction === "logout" ? "退出中..." : "退出登录"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="panel landing-panel auth-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">账号存档</p>
          <h2>登录后保存进度</h2>
        </div>
        <span className="tool-counter">支持游客试玩</span>
      </div>

      <div className="auth-mode-toggle">
        <button
          className={`filter-chip ${mode === "login" ? "filter-chip--active" : ""}`}
          onClick={() => switchMode("login")}
          type="button"
        >
          登录
        </button>
        <button
          className={`filter-chip ${mode === "register" ? "filter-chip--active" : ""}`}
          onClick={() => switchMode("register")}
          type="button"
        >
          注册
        </button>
      </div>

      <div className="auth-form-grid">
        <label className="field">
          <span className="field__label">用户名</span>
          <input
            className={`field__input ${validationErrors.username ? "field__input--invalid" : ""}`}
            disabled={isBusy}
            onChange={(event) => {
              setUsername(event.target.value);
              clearValidationError("username");
              onClearError();
            }}
            placeholder="例如：noise_archivist"
            type="text"
            value={username}
          />
          {validationErrors.username ? (
            <span className="field__error">{validationErrors.username}</span>
          ) : null}
        </label>

        <label className="field">
          <span className="field__label">密码</span>
          <input
            className={`field__input ${validationErrors.password ? "field__input--invalid" : ""}`}
            disabled={isBusy}
            onChange={(event) => {
              setPassword(event.target.value);
              clearValidationError("password");
              if (mode === "register") {
                clearValidationError("confirmPassword");
              }
              onClearError();
            }}
            placeholder="至少 8 位"
            type="password"
            value={password}
          />
          {validationErrors.password ? (
            <span className="field__error">{validationErrors.password}</span>
          ) : null}
        </label>

        {mode === "register" ? (
          <label className="field">
            <span className="field__label">确认密码</span>
            <input
              className={`field__input ${validationErrors.confirmPassword ? "field__input--invalid" : ""}`}
              disabled={isBusy}
              onChange={(event) => {
                setConfirmPassword(event.target.value);
                clearValidationError("confirmPassword");
                onClearError();
              }}
              placeholder="再次输入密码"
              type="password"
              value={confirmPassword}
            />
            {validationErrors.confirmPassword ? (
              <span className="field__error">{validationErrors.confirmPassword}</span>
            ) : null}
          </label>
        ) : null}
      </div>

      {authError ? <p className="auth-panel__error">{authError}</p> : null}

      <div className="auth-panel__footer">
        <p className="subtle-copy">
          {mode === "login"
            ? "登录后，关卡进度会持久保存在当前后端服务里。"
            : "新账号会从第一关开始，游客进度不会自动迁移。"}
        </p>
        <button
          className="action-button"
          disabled={isBusy}
          onClick={() => {
            void submitForm();
          }}
          type="button"
        >
          {authBusyAction === "login"
            ? "登录中..."
            : authBusyAction === "register"
              ? "注册中..."
              : mode === "login"
                ? "登录并继续"
                : "创建账号"}
        </button>
      </div>
    </section>
  );
}
