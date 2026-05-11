import { Background, Controls, Handle, Position, ReactFlow, type NodeProps } from '@xyflow/react';
import { useEffect, useMemo, useRef, useState } from 'react';

import type { RecruiterGraphNode } from './recruiterAnimation';
import type { RunStory } from './runStory';
import {
  fallbackLayout,
  layoutStrategyGraph,
  type LaidOutStrategyGraph,
  type StrategyFlowNode,
} from './strategyGraphLayout';

type StrategyGraphProps = {
  story: RunStory;
  selectedNodeId: string | null;
  onSelectNode: (node: RecruiterGraphNode) => void;
};

const defaultGraphBounds = { width: 980, height: 560 };
const minGraphBounds = { width: 360, height: 420 };
const nodeTypes = { strategy: StrategyGraphNode };

export function StrategyGraph({ story, selectedNodeId, onSelectNode }: StrategyGraphProps) {
  const [shellRef, graphBounds] = useStrategyGraphBounds();
  const fallbackGraph = useMemo(
    () => fallbackLayout(story.graphNodes, story.graphEdges, graphBounds),
    [graphBounds, story.graphEdges, story.graphNodes],
  );
  const [laidOutGraph, setLaidOutGraph] = useState<LaidOutStrategyGraph>(fallbackGraph);
  const graphKey = useMemo(
    () => `${graphBounds.width}x${graphBounds.height}:${story.graphNodes.map((node) => node.id).join('|')}`,
    [graphBounds.height, graphBounds.width, story.graphNodes],
  );
  const nodes = useMemo(
    () =>
      laidOutGraph.nodes.map((node) => {
        const selected = node.id === selectedNodeId;
        return {
          ...node,
          selected,
          data: { ...node.data, selected },
        };
      }),
    [laidOutGraph.nodes, selectedNodeId],
  );

  useEffect(() => {
    let canceled = false;
    setLaidOutGraph(fallbackGraph);
    void layoutStrategyGraph(story.graphNodes, story.graphEdges, graphBounds).then((graph) => {
      if (!canceled) {
        setLaidOutGraph(graph);
      }
    });
    return () => {
      canceled = true;
    };
  }, [fallbackGraph, story.graphEdges, story.graphNodes]);

  return (
    <div className="strategy-flow-shell" ref={shellRef}>
      <ReactFlow
        key={graphKey}
        className="strategy-flow"
        data-testid="strategy-flow"
        nodes={nodes}
        edges={laidOutGraph.edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.24 }}
        minZoom={0.2}
        maxZoom={1.6}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => onSelectNode(node.data.graphNode)}
      >
        <Background gap={24} size={1} className="strategy-flow-bg" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function useStrategyGraphBounds() {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const [bounds, setBounds] = useState(defaultGraphBounds);

  useEffect(() => {
    const element = shellRef.current;
    if (!element) {
      return;
    }

    const updateBounds = () => {
      const rect = element.getBoundingClientRect();
      const measuredWidth = rect.width || element.offsetWidth;
      const measuredHeight = rect.height || element.offsetHeight;
      const nextBounds = {
        width:
          measuredWidth > 0
            ? Math.max(minGraphBounds.width, Math.round(measuredWidth))
            : defaultGraphBounds.width,
        height:
          measuredHeight > 0
            ? Math.max(minGraphBounds.height, Math.round(measuredHeight))
            : defaultGraphBounds.height,
      };

      setBounds((currentBounds) =>
        currentBounds.width === nextBounds.width && currentBounds.height === nextBounds.height
          ? currentBounds
          : nextBounds,
      );
    };

    updateBounds();
    const observer = new ResizeObserver(updateBounds);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return [shellRef, bounds] as const;
}

function StrategyGraphNode({ data }: NodeProps<StrategyFlowNode>) {
  const node = data.graphNode;
  return (
    <div className="strategy-flow-node-shell">
      <Handle className="strategy-flow-handle" type="target" position={Position.Left} />
      <button
        className="strategy-flow-node"
        data-tone={node.tone}
        data-kind={node.kind}
        type="button"
        aria-pressed={data.selected}
      >
        <span>
          {node.kind}
          {node.sourceLabel && node.sourceKind !== 'all' ? <em className="node-source-badge">{node.sourceLabel}</em> : null}
        </span>
        <strong>{node.label}</strong>
        <small>{node.detail}</small>
      </button>
      <Handle className="strategy-flow-handle" type="source" position={Position.Right} />
    </div>
  );
}
