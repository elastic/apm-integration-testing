using System.Linq;
using Microsoft.AspNetCore.Mvc;

namespace TestAppDotnet.Controllers
{
	[Route("/oof")]
	[ApiController]
	public class OofController : ControllerBase
	{
		[HttpGet()]
		public ActionResult<string> Get() => throw new System.InvalidOperationException("500 Internal Server Error");
	}
}
