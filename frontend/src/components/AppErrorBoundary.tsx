import { Component, type ReactNode } from "react";
import "./AppErrorBoundary.css";

export default class AppErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="app-recovery" role="alert">
          <div>
            <h1>This page couldn’t load</h1>
            <p>The website may have updated. Reload to try again.</p>
            <button type="button" onClick={() => window.location.reload()}>
              Reload page
            </button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
