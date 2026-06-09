"""Runtime-facing ASK helper.

This module is the connector-safe bridge toward ``chat.runtime``: it exposes the
small default-dark helper that runtime can import/use in a later checkout-based
slice without editing the large runtime file through the GitHub connector.

The helper consumes the Stage 2 ASK acquisition seam honestly via the typed
``contemplation_result`` keyword. It does not render