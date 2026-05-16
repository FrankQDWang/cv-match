import type { RecruiterGraphDetailPayload, RecruiterGraphNode } from './recruiterAnimation';
import type { ReactNode } from 'react';
import type { SourceKind } from './types';

type NodeDetailPanelProps = {
  node: RecruiterGraphNode | null;
  candidatePanel?: ReactNode;
};

const sourceLabels: Record<SourceKind, string> = {
  cts: 'CTS',
  liepin: 'Liepin',
};

export function NodeDetailPanel({ node, candidatePanel }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className="node-detail-panel">
        <div className="node-detail-empty">
          <strong>未选择节点</strong>
          <span>点击策略图节点后查看业务细节。</span>
        </div>
      </div>
    );
  }

  return (
    <div className="node-detail-panel">
      <div className="node-detail-head">
        <span>{node.kind}</span>
        <h3>{node.label}</h3>
        <small>{node.sourceLabel ?? sourceLabel(node.sourceKind)}</small>
      </div>
      <div className="node-detail-body">
        {node.detailPayload ? <PayloadDetail payload={node.detailPayload} /> : <EmptyBusinessState />}
        {candidatePanel ? (
          <section className="node-detail-candidates" aria-label="节点候选人">
            {candidatePanel}
          </section>
        ) : null}
      </div>
    </div>
  );
}

function PayloadDetail({ payload }: { payload: RecruiterGraphDetailPayload }) {
  switch (payload.kind) {
    case 'reflection':
      return (
        <>
          <DetailRow label="轮次" value={`第 ${String(payload.roundNo)} 轮`} />
          <DetailBlock title="总结" value={payload.summary ? `总结：${payload.summary}` : ''} />
          <DetailBlock title="原因" value={payload.rationale} />
          <DetailBlock title="下一步" value={payload.nextDirection} />
        </>
      );
    case 'requirements':
      return (
        <>
          <DetailRow label="状态" value={triageStatusLabel(payload.triageStatus)} />
          <DetailList title="必须条件" values={payload.criteria.mustHaves} />
          <DetailList title="加分项" values={payload.criteria.niceToHaves} />
          <DetailList title="检索提示" values={payload.criteria.generatedQueryHints} />
        </>
      );
    case 'ctsRoundQuery':
      return (
        <>
          <DetailRow label="轮次" value={`第 ${String(payload.roundNo)} 轮`} />
          <DetailBlock title="关键词" value={payload.queryLabel} />
          <DetailList title="查询词" values={payload.queryTerms} />
          {payload.executedQueries && payload.executedQueries.length > 0 ? (
            <DetailList
              title="检索分支"
              values={payload.executedQueries.map((query) =>
                [
                  query.lane_type ?? 'default',
                  query.query_role,
                  query.query_terms.join(' / ') || query.keyword_query,
                  query.query_instance_id,
                ]
                  .filter(Boolean)
                  .join(' · '),
              )}
            />
          ) : null}
        </>
      );
    case 'ctsRoundResults':
      return (
        <>
          <DetailRow label="轮次" value={`第 ${String(payload.roundNo)} 轮`} />
          <DetailRow label="原始命中" value={`${String(payload.rawCandidateCount)} 人`} />
          <DetailRow label="新增候选人" value={`${String(payload.uniqueNewCount)} 人`} />
          {payload.recallCounts ? <DetailBlock title="召回分布" value={textFromRecord(payload.recallCounts)} /> : null}
        </>
      );
    case 'ctsRoundScoring':
      return (
        <>
          <DetailRow label="轮次" value={`第 ${String(payload.roundNo)} 轮`} />
          <DetailRow label="进入评分" value={`${String(payload.scoredCount ?? payload.newlyScoredCount)} 人`} />
          <DetailRow label="Fit" value={`${String(payload.fitCount)} 人`} />
          <DetailRow label="Not fit" value={`${String(payload.notFitCount)} 人`} />
        </>
      );
    case 'sourceQueue':
      return (
        <>
          <DetailRow label="渠道" value={sourceLabels[payload.sourceKind]} />
          <DetailRow label="状态" value={sourceRunStatusLabel(payload.status)} />
          <DetailRow label="授权" value={authStatusLabel(payload.authState ?? payload.connectionStatus)} />
          <DetailRow label="已扫描" value={`${String(payload.cardsScannedCount)} 张`} />
          <DetailRow label="去重候选人" value={`${String(payload.uniqueCandidatesCount)} 人`} />
          {payload.runtimeStatus ? <DetailRow label="运行状态" value={runtimeStatusLabel(payload.runtimeStatus)} /> : null}
          {payload.runtimeEventType ? <DetailRow label="最新事件" value={runtimeEventLabel(payload.runtimeEventType)} /> : null}
          {payload.runtimeEventSeq !== null && payload.runtimeEventSeq !== undefined ? (
            <DetailRow label="事件序号" value={payload.runtimeEventSeq} />
          ) : null}
          {payload.runtimeStatus ? (
            <>
              <DetailRow label="运行扫描" value={`${String(payload.runtimeCardsSeenCount ?? 0)} 张`} />
              <DetailRow label="已过滤" value={`${String(payload.runtimeCardsFilteredCount ?? 0)} 张`} />
              <DetailRow label="运行候选人" value={`${String(payload.runtimeCandidatesCount ?? 0)} 人`} />
              <DetailRow label="详情推荐" value={`${String(payload.runtimeDetailRecommendationsCount ?? 0)} 个`} />
              {payload.runtimeDetailState ? (
                <DetailRow label="详情状态" value={detailStateLabel(payload.runtimeDetailState)} />
              ) : null}
            </>
          ) : null}
          <DetailBlock title="提示" value={payload.warningMessage} />
        </>
      );
    case 'liepinCardSearch':
      return (
        <>
          <DetailRow label="已扫描" value={`${String(payload.cardsScannedCount)} 张`} />
          <DetailRow label="去重候选人" value={`${String(payload.uniqueCandidatesCount)} 人`} />
          <DetailRequestSummary payload={payload} />
        </>
      );
    case 'liepinDetailApproval':
      return <DetailRequestSummary payload={payload} />;
    case 'liepinCardCandidates':
      return (
        <>
          <DetailRow label="候选人数" value={`${String(payload.candidateReviewItemIds.length)} 人`} />
          <DetailRow label="最高分" value={scoreText(payload.bestScore)} />
          <DetailRow label="证据数" value={`${String(payload.candidateEvidenceRefs.length)} 条`} />
          <DetailRequestSummary payload={payload} />
        </>
      );
    case 'aggregation':
      return (
        <>
          <DetailRow label="候选人数" value={`${String(payload.candidateCount)} 人`} />
          <DetailRow label="最高分" value={scoreText(payload.bestScore)} />
          {payload.coverageStatus ? <DetailRow label="覆盖状态" value={coverageStatusLabel(payload.coverageStatus)} /> : null}
          {payload.finalizationRevision ? <DetailRow label="完成版本" value={payload.finalizationRevision} /> : null}
          {payload.finalizationReasonCode ? (
            <DetailRow label="完成原因" value={finalizationReasonLabel(payload.finalizationReasonCode)} />
          ) : null}
          {payload.identityMergeCount ? <DetailRow label="已合并身份" value={`${String(payload.identityMergeCount)} 个`} /> : null}
          {payload.ambiguousDuplicateCount ? (
            <DetailRow label="待确认重复" value={`${String(payload.ambiguousDuplicateCount)} 个`} />
          ) : null}
          {payload.canonicalResumeSelectedCount ? (
            <DetailRow label="标准简历" value={`${String(payload.canonicalResumeSelectedCount)} 份`} />
          ) : null}
          {payload.sourceStates && payload.sourceStates.length > 0 ? (
            <DetailList
              title="渠道状态"
              values={payload.sourceStates.map((source) =>
                [
                  sourceLabels[source.sourceKind],
                  runtimeStatusLabel(source.status),
                  `已扫描 ${String(source.cardsSeenCount)}`,
                  source.cardsFilteredCount > 0 ? `已过滤 ${String(source.cardsFilteredCount)}` : null,
                  `候选人 ${String(source.candidatesCount)}`,
                  source.detailRecommendationsCount > 0
                    ? `详情推荐 ${String(source.detailRecommendationsCount)}`
                    : null,
                  source.detailState ? detailStateLabel(source.detailState) : null,
                ]
                  .filter(Boolean)
                  .join(' · '),
              )}
            />
          ) : null}
          <DetailBlock title="最终报告" value={payload.finalReport} />
          {payload.stopReason ? <DetailRow label="结束原因" value={payload.stopReason} /> : null}
        </>
      );
    case 'job':
      return (
        <>
          <DetailRow label="岗位" value={payload.jobTitle} />
          <DetailRow label="检索模式" value={payload.sourceKinds.map((kind) => sourceLabels[kind]).join(' / ')} />
          <DetailBlock title="JD 预览" value={clip(payload.jdText, 260)} />
        </>
      );
  }
}

function DetailRequestSummary({
  payload,
}: {
  payload: Extract<
    RecruiterGraphDetailPayload,
    { kind: 'liepinCardSearch' | 'liepinCardCandidates' | 'liepinDetailApproval' }
  >;
}) {
  return (
    <>
      <DetailRow label="详情请求" value={`${String(payload.detailOpenRequestIds.length)} 个`} />
      <DetailList title="请求摘要" values={payload.requestSummaries} />
      <DetailBlock title="预算状态" value={payload.budgetText} />
    </>
  );
}

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="node-detail-row">
      <span>{label}</span>
      <strong>{hasValue(value) ? value : '暂无数据'}</strong>
    </div>
  );
}

function DetailBlock({ title, value }: { title: string; value: string | null | undefined }) {
  return (
    <section className="node-detail-block">
      <span>{title}</span>
      {hasValue(value) ? <p>{value}</p> : <p className="muted">暂无数据</p>}
    </section>
  );
}

function DetailList({ title, values }: { title: string; values: string[] }) {
  return (
    <section className="node-detail-block">
      <span>{title}</span>
      {values.length > 0 ? (
        <ul>
          {values.map((value, index) => (
            <li key={`${value}-${String(index)}`}>{value}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">暂无数据</p>
      )}
    </section>
  );
}

function EmptyBusinessState() {
  return (
    <div className="node-detail-empty">
      <strong>暂无业务细节</strong>
      <span>该节点还没有结构化详情。</span>
    </div>
  );
}

function triageStatusLabel(status: 'confirmed' | 'draft' | 'runtime') {
  if (status === 'confirmed') return '已确认';
  if (status === 'runtime') return '运行时解析';
  return '草稿';
}

function sourceLabel(sourceKind: RecruiterGraphNode['sourceKind']) {
  if (sourceKind === 'cts' || sourceKind === 'liepin') {
    return sourceLabels[sourceKind];
  }
  if (sourceKind === 'all') {
    return 'All sources';
  }
  return '未标记渠道';
}

function scoreText(score: number | null) {
  return score === null ? '暂无分数' : `${String(score)} 分`;
}

function sourceRunStatusLabel(status: string | null | undefined) {
  return statusLabel(status, {
    queued: '等待中',
    blocked: '已阻塞',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  });
}

function authStatusLabel(status: string | null | undefined) {
  return statusLabel(status, {
    not_required: '无需授权',
    login_required: '需要登录',
    login_in_progress: '登录中',
    verification_required: '需要验证',
    connected: '已连接',
    expired: '已过期',
    blocked: '已阻塞',
    disconnected: '未连接',
  });
}

function runtimeStatusLabel(status: string | null | undefined) {
  return statusLabel(status, {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    partial: '部分完成',
    blocked: '已阻塞',
    failed: '失败',
    cancelled: '已取消',
  });
}

function runtimeEventLabel(eventType: string | null | undefined) {
  return statusLabel(eventType, {
    source_lane_started: '渠道已启动',
    source_lane_completed: '渠道已完成',
    source_lane_blocked: '渠道已阻塞',
    source_lane_partial: '渠道部分完成',
    source_lane_failed: '渠道失败',
    source_lane_cancelled: '渠道已取消',
    detail_recommended: '已推荐详情',
    detail_approved: '详情已批准',
    detail_leased: '详情已预留',
    detail_completed: '详情已完成',
    detail_blocked: '详情已阻塞',
  });
}

function coverageStatusLabel(status: string | null | undefined) {
  return statusLabel(status, {
    pending: '等待覆盖',
    complete: '全部覆盖',
    degraded: '覆盖不完整',
    empty: '无候选人',
  });
}

function detailStateLabel(status: string | null | undefined) {
  return statusLabel(status, {
    detail_recommended: '已推荐详情',
    pending_approval: '等待批准',
    leased: '已预留详情',
    completed: '详情已完成',
    blocked: '详情已阻塞',
  });
}

function finalizationReasonLabel(reason: string | null | undefined) {
  return statusLabel(reason, {
    source_lanes_completed: '所有渠道已完成',
    source_lanes_degraded: '部分渠道不可用',
    detail_enrichment_applied: '详情已补充',
  });
}

function statusLabel(value: string | null | undefined, labels: Record<string, string>) {
  if (!value) {
    return '暂无状态';
  }
  return labels[value] ?? value;
}

function textFromRecord(value: Record<string, unknown>) {
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join(' / ');
}

function clip(value: string, maxLength: number) {
  const trimmed = value.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength - 1)}...`;
}

function hasValue(value: string | number | null | undefined): value is string | number {
  return value !== null && value !== undefined && String(value).trim().length > 0;
}
