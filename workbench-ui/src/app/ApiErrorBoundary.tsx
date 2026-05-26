import { Component, type ReactNode } from "react";
import { ErrorState } from "../design/components/states/ErrorState";
import { WorkbenchApiError } from "../api/client";
import { API_URL } from "../api/client";

interface Props {
  children: ReactNode;
}

interface State {
  error: WorkbenchApiError | null;
}

export class ApiErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: unknown): State {
    if (error instanceof WorkbenchApiError) {
      return { error };
    }
    return { error: null };
  }

  render() {
    const { error } = this.state;
    if (error) {
      return (
        <ErrorState
          whatFailed={`Workbench API unreachable at ${API_URL}`}
          mutationStatus="No corpus mutation occurred."
          reproducer="Run: core workbench api"
          retrySafety="Retry: safe (read-only)"
        />
      );
    }
    return this.props.children;
  }
}
