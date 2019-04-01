// AllowUnknownProperties: Allow unknown properties in an object
// Example: `type UserWithUnknown = AllowUnknownProperties<User>;`
//
// Converts:
//
//    interface User {
//      name: string;
//      age: number;
//      address: {
//        street: string;
//        city: string;
//      };
//    }
//
// To this:
//
//    type UserWithUnknown = {
//      name: string;
//      age: number;
//      [key: string]: unknown;
//      address: {
//        street: string;
//        city: string;
//        [key: string]: unknown;
//      };
//    };
export type AllowUnknownProperties<T> = T extends object
  ? { [P in keyof T]: AllowUnknownProperties<T[P]> } & {
      [key: string]: unknown;
    }
  : T;
