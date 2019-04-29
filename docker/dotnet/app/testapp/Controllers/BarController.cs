using System.Linq;
using Elastic.Apm.Api;
using Microsoft.AspNetCore.Mvc;

namespace TestAppDotnet.Controllers
{
	[Route("/bar")]
	[ApiController]
	public class BarController : ControllerBase
	{
		[HttpGet()]
		public ActionResult<string> Get() {
        string bar = "";
        ITransaction transaction = Elastic.Apm.Agent.Tracer.CurrentTransaction;
        transaction.CaptureSpan("bar", "just a regular bar",
        span =>
        {
           span.Tags["bar"] = "bar";
           bar = "bar";
        });
        return bar;
		}
	}
}
