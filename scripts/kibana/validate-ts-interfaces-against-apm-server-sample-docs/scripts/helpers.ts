// Allow unknown properties in an object
export type AllowUnknownProperties<T> = T extends object
  ? { [P in keyof T]: AllowUnknownProperties<T[P]> } & {
      [key: string]: unknown;
    }
  : T;
