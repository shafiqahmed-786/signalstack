import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/health(.*)",
]);

export default clerkMiddleware((auth, req) => {
  if (!isPublicRoute(req)) {
    auth().protect();
  }
});

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next
     * - static files
     * - images
     * - favicon
     */
    "/((?!_next|.*\\..*).*)",
    "/",
    "/(api|trpc)(.*)",
  ],
};