import React, { useState } from "react";

interface SafeMarkdownProps {
  content: string;
  maxCollapseChars?: number;
}

export const SafeMarkdown: React.FC<SafeMarkdownProps> = ({
  content,
  maxCollapseChars = 280,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!content) return null;

  const isLong = content.length > maxCollapseChars;
  const displayContent = isLong && !expanded ? content.slice(0, maxCollapseChars).trim() + "..." : content;

  // Helper to parse inline styles: **bold**, `code`, *italic*
  const renderInline = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    const tokenRegex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = tokenRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }
      const raw = match[0];
      if (raw.startsWith("**") && raw.endsWith("**")) {
        parts.push(
          <strong key={`${match.index}-b`} className="zuka-md-bold">
            {raw.slice(2, -2)}
          </strong>
        );
      } else if (raw.startsWith("`") && raw.endsWith("`")) {
        parts.push(
          <code key={`${match.index}-c`} className="zuka-md-code">
            {raw.slice(1, -1)}
          </code>
        );
      } else if (raw.startsWith("*") && raw.endsWith("*")) {
        parts.push(
          <em key={`${match.index}-i`} className="zuka-md-italic">
            {raw.slice(1, -1)}
          </em>
        );
      }
      lastIndex = tokenRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts;
  };

  // Split lines and parse blocks
  const lines = displayContent.split("\n");
  const blocks: React.ReactNode[] = [];
  let currentList: React.ReactNode[] = [];
  let listKey = 0;

  const flushList = () => {
    if (currentList.length > 0) {
      blocks.push(
        <ul key={`ul-${listKey++}`} className="zuka-md-list">
          {currentList}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }

    // Check for list items: - item, * item, • item, or 1. item
    const bulletMatch = trimmed.match(/^([-*•]|\d+\.)\s+(.+)$/);
    if (bulletMatch) {
      currentList.push(
        <li key={`li-${idx}`} className="zuka-md-li">
          {renderInline(bulletMatch[2])}
        </li>
      );
      return;
    }

    flushList();

    // Check for headings: #, ##, ###
    if (trimmed.startsWith("### ")) {
      blocks.push(
        <h4 key={`h4-${idx}`} className="zuka-md-h4">
          {renderInline(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith("## ")) {
      blocks.push(
        <h3 key={`h3-${idx}`} className="zuka-md-h3">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      blocks.push(
        <h2 key={`h2-${idx}`} className="zuka-md-h2">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
    } else {
      blocks.push(
        <p key={`p-${idx}`} className="zuka-md-p">
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  flushList();

  return (
    <div className="zuka-safe-markdown">
      {blocks}
      {isLong && (
        <button
          type="button"
          className="zuka-details-toggle"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show less ▲" : "Show details ▼"}
        </button>
      )}
    </div>
  );
};
