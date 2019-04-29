using System;
using System.Threading.Tasks;
using Elastic.Apm;
using Elastic.Apm.All;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace TestAspNetCoreApp
{
	public class Startup
	{
		private readonly IConfiguration _configuration;
		public Startup(IConfiguration configuration) => _configuration = configuration;

		public void Configure(IApplicationBuilder app, IHostingEnvironment env)
		{
			// /healthcheck is mapped before app.UseElasticApm -> as specified in the spec, it won't be traced.
			app.Map("/healthcheck", HealthCheck);

			app.UseElasticApm(_configuration);

			app.Map("/bar", Bar);
			app.Map("/foo", Foo);
			app.Map("/oof", Oof);

			app.Run(async context =>
			{
				if (context.Request.Path == "/")
					await context.Response.WriteAsync("OK");
				else
					context.Response.StatusCode = StatusCodes.Status404NotFound;
			});
		}

		private static void HealthCheck(IApplicationBuilder app) =>
			app.Run(async context => { await context.Response.WriteAsync("OK"); });

		private static void Foo(IApplicationBuilder app) =>
			app.Run(async context => { await context.Response.WriteAsync("foo"); });

		private static void Oof(IApplicationBuilder app) =>
			app.Run(context =>
			{
				context.Response.StatusCode = StatusCodes.Status500InternalServerError;
				throw new Exception("This is a test exception");
			});

		private static void Bar(IApplicationBuilder app) =>
			app.Run(async context =>
			{
				await Agent.Tracer.CurrentTransaction.CaptureSpan("barSpan", "sampleType",
					async () => { await Task.Delay(50); });

				await context.Response.WriteAsync("bar");
			});
	}
}
