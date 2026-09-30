import { useCallback, useEffect, useState } from "react";

export default function useLoad(fn, deps = [], poll = 0) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const run = useCallback(() => fn().then((data) => setState({ data, error: "", loading: false }))
    .catch((error) => setState({ data: null, error: error.message, loading: false })), deps); // eslint-disable-line

  useEffect(() => {
    run();
    if (poll) {
      const timer = setInterval(run, poll);
      return () => clearInterval(timer);
    }
  }, [run, poll]);

  return { ...state, reload: run };
}