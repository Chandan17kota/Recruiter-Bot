import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { routes } from "../routes";

/** Render the real app routes at `path`, with a fresh query cache and no retries. */
export function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...utils, router, search: () => new URLSearchParams(router.state.location.search) };
}

export const lastRequest = (requests: URL[], pathname: string) =>
  [...requests].reverse().find((u) => u.pathname === pathname);
