FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY src/ShopApi/ShopApi.csproj src/ShopApi/
RUN dotnet restore src/ShopApi/ShopApi.csproj
COPY src/ src/
RUN dotnet publish src/ShopApi/ShopApi.csproj -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app .
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "ShopApi.dll"]
