FROM mcr.microsoft.com/dotnet/core/sdk:2.2 AS build
COPY . /src/

WORKDIR /src
RUN dotnet restore
RUN dotnet publish -c Release -o out

## Alpine image produces a segmentation fault:
##        further details: https://github.com/aspnet/EntityFrameworkCore/issues/14504
## FROM mcr.microsoft.com/dotnet/core/aspnet:2.2-alpine AS runtime
FROM mcr.microsoft.com/dotnet/core/aspnet:2.2 AS runtime
WORKDIR /app
COPY --from=build src/out ./
EXPOSE 80
ENTRYPOINT ["dotnet", "TestAspNetCoreApp.dll"]