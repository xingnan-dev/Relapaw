export function Understand() {
  return (
    <section aria-labelledby="understand-title">
      <p className="eyebrow">UNDERSTAND</p>
      <h2 id="understand-title">它怎么啦？</h2>
      <ol className="step-rail" aria-label="理解流程"><li className="active">输入</li><li>区分</li><li>安全</li><li>下一步</li></ol>
      <label htmlFor="owner-input">描述你看到的情况</label>
      <textarea id="owner-input" rows={7} placeholder="先写下发生了什么，以及你是怎么理解的……" />
      <div className="media-actions" aria-label="Media placeholders">
        <button type="button" disabled>语音</button>
        <button type="button" disabled>图片</button>
        <button type="button" disabled>视频</button>
      </div>
      <div className="lens-grid">
        <label className="lens-card"><strong>发生了什么</strong><span>只记录可以观察到的事实</span><textarea rows={3} aria-label="发生了什么" /></label>
        <label className="lens-card interpretation"><strong>你的理解</strong><span>把你的想法单独保留下来</span><textarea rows={3} aria-label="你的理解" /></label>
      </div>
      <button className="primary" type="button">保存手工记录</button>
      <div className="evidence-stack" aria-label="未来分析步骤占位"><div>Context</div><div>Historical Context</div><div>Possible Explanations</div><div>Next Step</div></div>
      <p className="notice">Phase 0.1：当前不会进行 AI 分析、医学判断或自动生成 Observation。</p>
    </section>
  );
}
