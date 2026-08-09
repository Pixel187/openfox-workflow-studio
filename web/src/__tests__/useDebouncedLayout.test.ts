import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebouncedLayout } from "../hooks/useDebouncedLayout";
import { api } from "../api";

describe("useDebouncedLayout", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("persiste une seule fois après plusieurs changements dans la fenêtre de debounce", () => {
    const putLayout = vi.spyOn(api, "putLayout").mockResolvedValue({});
    const { result } = renderHook(() => useDebouncedLayout("demo"));

    act(() => {
      result.current([{ id: "s1", position: { x: 1, y: 1 } }]);
      result.current([{ id: "s1", position: { x: 2, y: 2 } }]);
      result.current([{ id: "s1", position: { x: 3, y: 3 } }]);
    });
    expect(putLayout).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(putLayout).toHaveBeenCalledTimes(1);
    expect(putLayout).toHaveBeenCalledWith("demo", {
      nodes: [{ id: "s1", position: { x: 3, y: 3 } }],
    });
  });

  it("ne persiste rien sans workflowId", () => {
    const putLayout = vi.spyOn(api, "putLayout").mockResolvedValue({});
    const { result } = renderHook(() => useDebouncedLayout(null));

    act(() => {
      result.current([{ id: "s1", position: { x: 1, y: 1 } }]);
      vi.advanceTimersByTime(500);
    });
    expect(putLayout).not.toHaveBeenCalled();
  });

  it("annule la persistance précédente quand un nouveau changement arrive", () => {
    const putLayout = vi.spyOn(api, "putLayout").mockResolvedValue({});
    const { result } = renderHook(() => useDebouncedLayout("demo"));

    act(() => {
      result.current([{ id: "s1", position: { x: 1, y: 1 } }]);
      vi.advanceTimersByTime(300);
      result.current([{ id: "s1", position: { x: 9, y: 9 } }]);
      vi.advanceTimersByTime(500);
    });
    expect(putLayout).toHaveBeenCalledTimes(1);
    expect(putLayout).toHaveBeenCalledWith("demo", {
      nodes: [{ id: "s1", position: { x: 9, y: 9 } }],
    });
  });
});