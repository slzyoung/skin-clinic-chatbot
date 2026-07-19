export const configKeys = {
  all: ['configs'] as const,
  lists: () => [...configKeys.all, 'list'] as const,
  detail: (key: string) => [...configKeys.all, 'detail', key] as const,
};
