import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Onboarding } from "./Onboarding";

afterEach(() => {
  vi.useRealTimers();
});

describe("onboarding paper flow", () => {
  it("moves forward and back one sheet at a time", () => {
    vi.useFakeTimers();
    render(<Onboarding onComplete={vi.fn()} />);

    const next = screen.getByRole("button", { name: "翻到下一页" });
    fireEvent.click(next);
    expect(next).toBeDisabled();
    act(() => vi.advanceTimersByTime(850));
    expect(screen.getByRole("heading", { name: "看见变化，不替它说话" })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "返回" }));
    act(() => vi.advanceTimersByTime(850));
    expect(screen.getByRole("heading", { name: "先看见，再慢慢理解" })).toBeVisible();
  });

  it("reveals the profile underlay before completing the final turn", () => {
    vi.useFakeTimers();
    const onComplete = vi.fn();
    render(<Onboarding onComplete={onComplete} finalUnderlay={<p>档案页底层</p>} />);

    fireEvent.click(screen.getByRole("button", { name: "翻到下一页" }));
    act(() => vi.advanceTimersByTime(850));
    fireEvent.click(screen.getByRole("button", { name: "翻到下一页" }));
    act(() => vi.advanceTimersByTime(850));
    fireEvent.click(screen.getByRole("button", { name: "开始建立档案" }));

    expect(screen.getByText("档案页底层")).toBeInTheDocument();
    expect(onComplete).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(850));
    expect(onComplete).toHaveBeenCalledOnce();
  });

  it("supports a non-mutating review mode with a clear close action", () => {
    const onComplete = vi.fn();
    render(<Onboarding reviewMode onComplete={onComplete} />);
    fireEvent.click(screen.getByRole("button", { name: "关闭介绍" }));
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
