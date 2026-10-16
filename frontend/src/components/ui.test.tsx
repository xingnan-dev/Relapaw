import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge, Button, SectionHeader, StatusNotice, Surface } from "./ui";

describe("design system primitives", () => {
  it("keeps Button native semantics and exposes busy state", () => {
    render(<Button variant="primary" busy>正在保存</Button>);
    const button = screen.getByRole("button", { name: "正在保存" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveClass("ui-button--primary");
  });

  it("makes notice urgency explicit instead of relying on color", () => {
    render(<StatusNotice tone="danger" role="alert" title="Safety blocked">没有调用模型。</StatusNotice>);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Safety blocked");
    expect(alert).toHaveTextContent("没有调用模型");
    expect(alert).toHaveClass("status-notice--danger");
  });

  it("does not turn static guidance into an unsolicited live region", () => {
    render(<StatusNotice tone="warning" title="模型生成">尚未确认</StatusNotice>);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByText("模型生成")).toBeInTheDocument();
  });

  it("provides a composable semantic surface", () => {
    render(<Surface tone="subtle" aria-label="输入预览">内容</Surface>);
    expect(screen.getByLabelText("输入预览")).toHaveClass("ui-surface--subtle");
  });

  it("exposes badge meaning as text", () => {
    render(<Badge tone="warning">待确认</Badge>);
    expect(screen.getByText("待确认")).toHaveClass("ui-badge--warning");
  });

  it("provides a page-level heading without hiding its description", () => {
    render(<SectionHeader eyebrow="TODAY" title="今天" description="从真实记录开始。" action={<Button>添加</Button>} />);
    expect(screen.getByRole("heading", { name: "今天" })).toBeInTheDocument();
    expect(screen.getByText("从真实记录开始。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "添加" })).toBeInTheDocument();
  });
});
